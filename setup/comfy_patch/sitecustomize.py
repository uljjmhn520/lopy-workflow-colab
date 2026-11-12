import inspect
import types
import typing
import torch
import torch._library.infer_schema as s

old_infer_schema = s.infer_schema

def patched_infer_schema(prototype_function, mutates_args=()):
    sig = inspect.signature(prototype_function)
    new_params = []
    gl = {
        'torch': torch,
        'Tensor': torch.Tensor,
        'typing': typing,
        'Optional': typing.Optional,
        'Sequence': typing.Sequence,
        'List': typing.List,
        'NoneType': type(None)
    }
    for p in sig.parameters.values():
        ann = p.annotation
        if isinstance(ann, str):
            try:
                ann = eval(ann, gl)
            except Exception:
                pass
        if isinstance(ann, types.UnionType):
            ann = typing.Union[ann.__args__]
        new_params.append(p.replace(annotation=ann))
    ret_ann = sig.return_annotation
    if isinstance(ret_ann, str):
        try:
            ret_ann = eval(ret_ann, gl)
        except Exception:
            pass
    prototype_function.__signature__ = sig.replace(parameters=new_params, return_annotation=ret_ann)
    return old_infer_schema(prototype_function, mutates_args)

s.infer_schema = patched_infer_schema

for k, v in list(s.SUPPORTED_PARAM_TYPES.items()):
    origin = typing.get_origin(k)
    args = typing.get_args(k)
    if origin in (list, typing.List, typing.Sequence) and args:
        try:
            s.SUPPORTED_PARAM_TYPES[list[args[0]]] = v
        except Exception:
            pass

# Patch SDPA for PyTorch 2.4 compatibility where enable_gqa kwarg does not exist
_orig_sdpa = torch.nn.functional.scaled_dot_product_attention

def _compat_sdpa(query, key, value, *args, **kwargs):
    enable_gqa = kwargs.pop('enable_gqa', False)
    if enable_gqa and query.shape[-3] != key.shape[-3]:
        q_heads = query.shape[-3]
        k_heads = key.shape[-3]
        if q_heads % k_heads == 0:
            rep = q_heads // k_heads
            key = key.repeat_interleave(rep, dim=-3)
            value = value.repeat_interleave(rep, dim=-3)
    return _orig_sdpa(query, key, value, *args, **kwargs)

torch.nn.functional.scaled_dot_product_attention = _compat_sdpa

