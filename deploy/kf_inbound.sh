#!/usr/bin/env bash
FUNC_NAME=kf_inbound
ENTRY_POINT=kf_inbound
ENV_VARS_FILE=environment/dev.env.yml
RUNTIME=python37
COMMAND="gcloud functions deploy ${FUNC_NAME} --entry-point ${ENTRY_POINT} --runtime ${RUNTIME} --env-vars-file ${ENV_VARS_FILE} --trigger-http"
echo $COMMAND
eval $COMMAND
