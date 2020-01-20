#!/usr/bin/env bash
GCP_PROJECT="saas-rally-dev-integrations"
FUNC_NAME=kf_evaluator
ENTRY_POINT=kf_evaluateOCM
ENV_VARS_FILE=environment/dev.env.yml
RUNTIME=python37
TRIGGER_TOPIC=kf-ocm-evaluate
#TRIGGER_TOPIC=kf-blowhole
TRIGGER_EVENT=providers/cloud.pubsub/eventTypes/topic.publish

COMMAND="gcloud functions deploy ${FUNC_NAME} --entry-point ${ENTRY_POINT} --runtime ${RUNTIME} --env-vars-file ${ENV_VARS_FILE} \
         --trigger-resource ${TRIGGER_TOPIC} --trigger-event ${TRIGGER_EVENT}"

#         --trigger-topic ${TRIGGER_TOPIC}"

echo $COMMAND
eval $COMMAND

#gcloud auth activate-service-account --key-file=$CREDS_FILE
#gcloud config set project $GCP_PROJECT

