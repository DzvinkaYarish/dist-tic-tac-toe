# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from protos import share_id_pb2 as protos_dot_share__id__pb2


class IdSharingStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ShareId = channel.unary_unary(
                '/IdSharing/ShareId',
                request_serializer=protos_dot_share__id__pb2.ShareIdRequest.SerializeToString,
                response_deserializer=protos_dot_share__id__pb2.ShareIdResponse.FromString,
                )


class IdSharingServicer(object):
    """Missing associated documentation comment in .proto file."""

    def ShareId(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_IdSharingServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ShareId': grpc.unary_unary_rpc_method_handler(
                    servicer.ShareId,
                    request_deserializer=protos_dot_share__id__pb2.ShareIdRequest.FromString,
                    response_serializer=protos_dot_share__id__pb2.ShareIdResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'IdSharing', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class IdSharing(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def ShareId(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/IdSharing/ShareId',
            protos_dot_share__id__pb2.ShareIdRequest.SerializeToString,
            protos_dot_share__id__pb2.ShareIdResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
