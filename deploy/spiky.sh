#!/usr/bin/env bash
FUNC_NAME=spikeTheDatabase
ENTRY_POINT=spikeTheDatabase
ENV_VARS_FILE=environment/spikey.env.yml
RUNTIME=python37
COMMAND="gcloud functions deploy ${FUNC_NAME} --runtime ${RUNTIME} --entry-point ${ENTRY_POINT} --env-vars-file ${ENV_VARS_FILE} --trigger-http"
echo $COMMAND
eval $COMMAND
