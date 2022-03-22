import logging
from typing import Any, MutableMapping, Optional

from cloudformation_cli_python_lib import (
    BaseHookHandlerRequest,
    HandlerErrorCode,
    Hook,
    HookInvocationPoint,
    OperationStatus,
    ProgressEvent,
    SessionProxy,
    exceptions,
)

from .models import HookHandlerRequest, TypeConfigurationModel

# Use this logger to forward log messages to CloudWatch Logs.
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
TYPE_NAME = "DemoOrg::CloudFront::BehaviorHook"

LOG.debug(f"Starting {TYPE_NAME} ....")

hook = Hook(TYPE_NAME, TypeConfigurationModel)
test_entrypoint = hook.test_entrypoint


def _check_viewer_request(lambda_function_associations, lambda_arn):
    LOG.debug(f"Checking function associations {lambda_function_associations}")
    viewer_request_function = list(filter(lambda function: function['EventType'] == 'viewer-request', lambda_function_associations))
    if viewer_request_function:
        if viewer_request_function[0]["LambdaFunctionARN"] == lambda_arn:
            LOG.debug("Matching function ARN found for viewer request")
            return True
        else:
            LOG.debug("No matching function ARN found for viewer request")
            return False
    else:
        LOG.debug("No viewer request function found for behavior")
        return False


def _validate_behavior_viewer_request_lambda_arn(progress, target_name, resource_properties, ssm_key, session):
    try:
        LOG.debug(f"Details of resource_properties: {resource_properties}")

        # Get the expected ARN from SSM Parameter Store
        client = session.client('ssm')
        expected_arn_ssm = client.get_parameter(
            Name=ssm_key,
            WithDecryption=True
        )
        expected_arn = expected_arn_ssm.get("Parameter", {}).get("Value")
        LOG.debug(f"SSM Param - expected arn: {expected_arn}")

        if resource_properties:
            if resource_properties["DistributionConfig"]["DefaultCacheBehavior"]:
                if resource_properties["DistributionConfig"]["DefaultCacheBehavior"]["LambdaFunctionAssociations"]:
                    if _check_viewer_request(resource_properties["DistributionConfig"]["DefaultCacheBehavior"]["LambdaFunctionAssociations"], expected_arn):
                        LOG.debug("Default Behavior: Valid Viewer Request Function Found")
                    else:
                        progress.status = OperationStatus.FAILED
                        progress.message = f"Default Behavior: No Valid Viewer Request Function Found"
                        progress.errorCode = HandlerErrorCode.NonCompliant
                        LOG.debug(" Default Behavior: Valid Viewer Request Function Found")
                else:
                    progress.status = OperationStatus.FAILED
                    progress.message = f"No Lambda Functions associated with Default Behavior"
                    progress.errorCode = HandlerErrorCode.NonCompliant
                    LOG.debug("No Lambda Functions associated with Default Behavior")

                # Set
                progress.status = OperationStatus.SUCCESS
                progress.message = f"Successfully invoked HookHandler for target {target_name} "
                LOG.debug(f"Successfully invoked HookHandler for target {target_name}")
            else:
                progress.status = OperationStatus.FAILED
                progress.message = f"No Default Cache Behavior Found"
                progress.errorCode = HandlerErrorCode.NotFound
                LOG.debug("No Default Cache Behavior Found")

            if resource_properties["DistributionConfig"]["CacheBehaviors"]:
                for cacheBehavior in resource_properties["DistributionConfig"]["CacheBehaviors"]:
                    if _check_viewer_request(cacheBehavior["LambdaFunctionAssociations"], expected_arn):
                        LOG.debug("Cache Behavior: Valid Viewer Request Function Found")
                    else:
                        progress.status = OperationStatus.FAILED
                        progress.message = f"Cache Behavior: No Valid Viewer Request Function Found"
                        progress.errorCode = HandlerErrorCode.NonCompliant
                        LOG.debug(f"Cache Behavior: {cacheBehavior} no Valid Viewer Request Function Found")
            else:
                LOG.debug(f"No cache behaviors found")

        else:
            progress.status = OperationStatus.FAILED
            progress.message = f"Failed to verify ARN for target {target_name}."
            progress.errorCode = HandlerErrorCode.InternalFailure

    except TypeError as e:
        progress.status = OperationStatus.FAILED
        progress.message = f"was not expecting type {e}."
        progress.errorCode = HandlerErrorCode.InternalFailure

    LOG.debug(f"Return Details: {progress.message}, {progress.status}, {progress.errorCode} ")
    return progress


@hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)
@hook.handler(HookInvocationPoint.UPDATE_PRE_PROVISION)
def pre_create_handler(
        session: Optional[SessionProxy],
        request: HookHandlerRequest,
        callback_context: MutableMapping[str, Any],
        type_configuration: TypeConfigurationModel
) -> ProgressEvent:
    target_model = request.hookContext.targetModel
    target_name = request.hookContext.targetName
    LOG.debug(request)
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS
    )
    # # Make sure this hook is running against the expected resource type
    if "AWS::CloudFront::Distribution" == target_name:
        LOG.info(f"Successfully invoked PreCreateHookHandler for target {target_name}")
        LOG.debug(f"DEBUG SSM Parameter Store Key location for compliant ARN: {type_configuration.SsmKey}")
        return _validate_behavior_viewer_request_lambda_arn(progress, target_name, request.hookContext.targetModel.get("resourceProperties"), type_configuration.SsmKey, session)
    else:
        return ProgressEvent.failed(HandlerErrorCode.InternalFailure, f"Unknown target type: {target_name}")

