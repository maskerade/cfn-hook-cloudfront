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
TYPE_NAME = "DemoOrg::CloudFront::BehaviorHook"

hook = Hook(TYPE_NAME, TypeConfigurationModel)
test_entrypoint = hook.test_entrypoint


def _validate_behavior_viewer_request_lambda_arn(progress, target_name, resource_properties, ssm_key, session):
    LOG.debug("In the function - validate_behavior_viewer_request_lambda_arn")
    try:
        if resource_properties:
            LOG.debug(f"DEBUG Details of resource_properties: {resource_properties}")

        else:
            progress.status = OperationStatus.FAILED
            progress.message = f"Failed to verify ARN for target {target_name}."
            progress.errorCode = HandlerErrorCode.InternalFailure

    except TypeError as e:
        progress.status = OperationStatus.FAILED
        progress.message = f"was not expecting type {e}."
        progress.errorCode = HandlerErrorCode.InternalFailure

    LOG.info(f"Results Message: {progress.message}")

    return progress


@hook.handler(HookInvocationPoint.CREATE_PRE_PROVISION)
def pre_create_handler(
        session: Optional[SessionProxy],
        request: HookHandlerRequest,
        callback_context: MutableMapping[str, Any],
        type_configuration: TypeConfigurationModel
) -> ProgressEvent:
    target_model = request.hookContext.targetModel
    target_name = request.hookContext.targetName
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS
    )
    # TODO: put code here

    # Make sure this hook is running against the expected resource type
    if "AWS::CloudFront::Distribution" == target_name:
        LOG.info(f"Successfully invoked PreCreateHookHandler for target {target_name}")
        LOG.debug(f"DEBUG SSM Parameter Store Key location for compliant ARN: {type_configuration.SsmKey}")
        _validate_behavior_viewer_request_lambda_arn(progress, target_name, request.hookContext.targetModel.get("resourceProperties"), type_configuration.SsmKey, session)
        # return _validate_ec2_instance_imageid(progress, target_name, request.hookContext.targetModel.get(
        # "resourceProperties"), type_configuration.SsmKey, session)
    else:
        return ProgressEvent.failed(HandlerErrorCode.InternalFailure, f"Unknown target type: {target_name}")






    # Example:
    try:
        # Reading the Resource Hook's target properties
        resource_properties = target_model.get("resourceProperties")

        if isinstance(session, SessionProxy):
            client = session.client("s3")
        # Setting Status to success will signal to cfn that the hook operation is complete
        progress.status = OperationStatus.SUCCESS
    except TypeError as e:
        # exceptions module lets CloudFormation know the type of failure that occurred
        raise exceptions.InternalFailure(f"was not expecting type {e}")
        # this can also be done by returning a failed progress event
        # return ProgressEvent.failed(HandlerErrorCode.InternalFailure, f"was not expecting type {e}")

    return progress


@hook.handler(HookInvocationPoint.UPDATE_PRE_PROVISION)
def pre_update_handler(
        session: Optional[SessionProxy],
        request: BaseHookHandlerRequest,
        callback_context: MutableMapping[str, Any],
        type_configuration: TypeConfigurationModel
) -> ProgressEvent:
    target_model = request.hookContext.targetModel
    progress: ProgressEvent = ProgressEvent(
        status=OperationStatus.IN_PROGRESS
    )
    # TODO: put code here

    # Example:
    try:
        # A Hook that does not allow a resource's encryption algorithm to be modified

        # Reading the Resource Hook's target current properties and previous properties
        resource_properties = target_model.get("resourceProperties")
        previous_properties = target_model.get("previousResourceProperties")

        if resource_properties.get("encryptionAlgorithm") != previous_properties.get("encryptionAlgorithm"):
            progress.status = OperationStatus.FAILED
            progress.message = "Encryption algorithm can not be changed"
        else:
            progress.status = OperationStatus.SUCCESS
    except TypeError as e:
        progress = ProgressEvent.failed(HandlerErrorCode.InternalFailure, f"was not expecting type {e}")

    return progress


@hook.handler(HookInvocationPoint.DELETE_PRE_PROVISION)
def pre_delete_handler(
        session: Optional[SessionProxy],
        request: BaseHookHandlerRequest,
        callback_context: MutableMapping[str, Any],
        type_configuration: TypeConfigurationModel
) -> ProgressEvent:
    # TODO: put code here
    return ProgressEvent(
        status=OperationStatus.SUCCESS
    )
