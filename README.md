# kingfisher

Can GCP Functions be used to implement Pigeon webhook functionality?
   Does a GCP Function approach provide benefits? in these dimensions:
       Simplicity
       Coherence
       Maintainability
       Scalability
       Modularity
       Pipelining
       Monitoring


   Assuming the presence of Kafka in the GCP project, and access to the prod-object-change-notification-alm-5 topic
   can GCP functions be automatically invoked subsequent to a message being published on the target topic?

       Confluent has a Kafka Connector for an HTTP sink (Kafka Connect Http Sink Connector).
          It works by converting the Kafka messsage to a String and then POSTs 
            the message to the configured endpoint 
          It is up to the GCP platform to start up multiple copies of the target function to meet the "demand"
       
   What about strict chronological ordering of the OCM stream? 
      The price for this is likely to be higher than the value delivered. It complexifies the whole mechanism.

   Google Cloud Platform folks have writtent a Kafka Connector to Google PubSub which can publish
   messages from a Kafka topic to a PubSub topic.  
       You have to build the connector from source and then run it on a machine that has access to your
       GCP project environment.  An potential approach to this is to spin up a GCP CE Linux VM.

  
   First pass at a pipeline approach for webhooks

      Google PubSub topics involved:
          kf-ocm-evaluate
          kf-webhook-ready
          kf-webhook-nogo
          kf-webhook-fired

         Function1: ingest and obtain webhooks and conditions  (kf-ingester)

                     requires db query to get webhook targets and expressions relevant to 
                          sub_id, object_type, action

                     publish message, webhooks, conditions to KF_OCM_EVALUATE

         Function2:  triggered by kf-ocm-evaluate topic (kf-evaluator)
                     Evaluate message against all applicable webhooks conditions 
                     uniquify conditions such that each condition is evaluated once and saved by id
                     for each webhook, replace the list of condition ids with a dict of cond-id, eval-result
                     identify the webhooks whose cond dict has a false eval result
                     identify the webhooks whose cond dict has all true results
                     for non-firing webhooks
                         publish transaction_id, sub_id, timestamp, failing cond-id(s) to PubSub topic kf-webhook-nogo
                     for firing webhooks
                         envelope carries transaction, sub_id, timestamp, qualifying condition(s)
                         publish envelope, payload to PubSub topic kf-webhook-ready

         Function3: triggered by kf-webhook-read topic (kf-webcannon)
                    webcannon.py  POST message to webhook URL

   ---------------------------------------------------------------------------------------------------

      Advantages:
          An HTTP triggered function (by virtue of the Kafka HTTP sink connector) gets a string payload
            that can be turned into a JSON object.  Don't have to mess with schema definitions.                      
          Separation of concerns, functions can vary independently. 

          Kafka connector is not part of the function set code. 

          Functions have no idea of Kafka, topics, partitions.

          Functions are auto-scaled as needed.  Faster functions may have a smaller set of concurrent invocations.
          Slower functions (firing the webhooks) can have more invocations.

          Separate logging per function, can be used in Splunk identification

          Decouple logic elements via buffers (PubSub topics)

          Visibility points in the process. 
             Use Function logs / Splunk to determine how many stages an OCM went through.  
             Was it ingested and were webhooks and conditions found?
             Did it pass expression evaluations?
             If it did not pass, which expressions did not evaluate as true?
             Was the webhook fired successfully?  
             Metrics around webhooks for a sub_id in some useful timeframe 
                (5 min, 15 min, 1 hour, this day, yesterday)

          Potential to replay firable webhooks.

          Periodic reports on hourly, daily, weekly, monthly basis by sub_id
             number of webhooks used / number of webhooks defined-enabled
             webhooks not used
             expressions used-matched / expressions evaluated
             expressions not used
             webhook success rate
             webhook failures
             webhook retries
             webhook matches by object-type
             percentage of messages requiring a webhook firing

          Cost is use based

      Disadvantages

          Non-deterministic pricing, might be predictable over time

          Dependence on Kafka infrastructure (addition of Kafka Web service connector)

          Secured call of function requires some overhead in function to authenticate
 
          Keeping connector auth info in synch with GCP function auth info (operations admin task)

          Start-up cost in time

---------------------------------------------------------------------------------------------------

Kingfisher considerations

   Database

	Postgres DB instance (atoms-hackathon) has a kingfisher database with these tables:             

	CONDITION
	  ObjectUUID
	  SubscriptionID
	  AttributeID
	  AttributeName
	  Operator
	  Value

	WEBHOOK
	  ObjectUUID
	  SubscriptionID
	  CreationDate
	  CreatedBy         who originally created this webhook
	  OwnerID           who owns this webhook now (must be related to SubscriptionID)
	  Name              label/blurb about what this webhook is for or what it does on the receiving end
	  AppName           what app on the customer end is using this 
	  AppUrl            what is the url for the app on the customer where one can get more information about the app and its API
	  Protocol          http (default) or https
	  TargetUrl         URI where this webhook will be posted
	  ObjectTypes       collection of ObjectType items (can be empty)
	  Disabled          1 or 0
	  Conditions        collection of Conditionn items
	  LastUpdateDate    creation date or date of last update
	  ObjectVersion     1 on creation, incremented for each update activity

   Endpoints for Kingfisher
       while a Webhook entry is identified in the database uniquely by the ObjectUUID
       from the user's viewpoint a tuple of (Name, AppName, AppUrl, TargetUrl, CreatedBy, OwnerID) identifies the Webhook

       Every request results in obtaining the APIKey from the request header (ZSESSIONID) and querying zuul to check
       for validity and a request to AC for SubscriptionID (if zuul doesn't supply it)

       Have an implementation that puts up a fight against DDOS  (may be moot, our HA-Proxy already does this)

       Have an implementation that ensures that SQL-injection using customer supplied data is explicitly disallowed 

       do not rely on anything in the request header (other than the ZSESSIONID) 

       Endpoint: /webhook[?query_string]

       PUT  (Create)
           required fields
              Name
              TargetUrl
              Condition  (Attribute relational_operator Value)
           
            optional 
               AppName
               AppUrl
               Protocol     (default to http)
               ObjectTypes  (default to nothing which indicates all qualifying entities are covered by this webhook)
               Disabled     (default to 1)

       GET  (Read)

           query_string must contain:
                 ObjectUUID
              OR SubscriptionID,OwnerID

              AND can have any/all of:
                 CreationDate relation value
                 Name    [!]= value
                 AppName [!]= value
                 AppUrl  [!]= value
                 TargetUrl  = value
                 Protocol   = http / https
                 ObjectTypes [!]in comma_separated_list_of_values (Artifact,Story,Defect,Task,TestCase,DefectSuite,Release,Iteration,Milestone, PortfolioItem/subtyp,Plan,Objective)
                 ObjectVersion [!]= value 
                 LastUpdateDate relation date_value
                 Disabled   =  0 / 1

                 CreatedBy reln date_value

            ?? what about a query to get all webhook items matching an condition or has a specific attribute in the condition
 
       POST (Update)
           query_string must contain:
                 ObjectUUID
              OR SubscriptionID,OwnerID,WebhookID

           and the payload must have at least one or more of the following attribute-value assignments 
               Name           cannot be null
               TargetUrl      cannot be null
               Protocol       cannot be null
               OwnerID        cannot be null, must be a UUID belonging to the SubscriptionID
               AppName
               AppUrl
               ObjectTypes    can be single string value or a comma separated list of strings (no single value can be more than 32 bytes)

             can have 
               OldCondition (attribute relation value)
               NewCondition (attribute relation value)

             these attrs are specifically disallowed
               WebhookID
               SubscriptionID
               CreationDate
               CreatedBy
               ObjectVersion
               LastUpdateDate

       DELETE 
           query_string must contain:
                 ObjectUUID
           

   Webhook Create endpoint processing sequence
      1) look for an existing webhook with same CreatedBy,Protocol,TargetUrl,and an associated Condition matching candidate
         if one exists, return a 422 (duplicate resource already exists)

      2) Condition is specified (ie, 1 attribute, valid relation, value consistent with attribute and relation) {attribute:attr_uuid,relation:operator,value:attribute_value}
           a) determine syntax of Condition for the candidate Webook, 
           b) query Condition table for matching entries

              b.1) no such Condition currently exists
                   create Webhook entry (the Condition attribute will be empty), save the UUID
                   create the Condition entry using the just created Webhook entry's UUID as the Condition's WebhookID
                   update the Webhook, with the Condition UUID as the initial value for the Condition collection

              b.2) an Condition currently exists matching the 3-tuple of the candidate (attribute, relation, value)
                   create Webhook entry using the UUID of the matching expression as another item in the Condition collection

            periodically the application should query for any Webhook entry that was created prior to n hours ago, and
            delete it if the Condition collection is empty

          
      3) Condition(s) is specified (in JSON, Condition is a list of dictionaries, with each dictionary conforming to the syntax 
         specified above in 2

            create the Webhook entry, save the UUID
            processing is a rehash of the above for each Condition
            when all Condition items have either been created or identified, 
               update the newly created Webhook entry Condition collection


---------------------------------------------------------------------------------------------------
