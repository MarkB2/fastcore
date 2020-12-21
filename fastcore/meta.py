# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/07_meta.ipynb (unless otherwise specified).

__all__ = ['test_sig', 'FixSigMeta', 'PrePostInitMeta', 'AutoInit', 'NewChkMeta', 'BypassNewMeta', 'empty2none',
           'anno_dict', 'use_kwargs_dict', 'use_kwargs', 'delegates', 'method', 'funcs_kwargs']

# Cell
from .imports import *
from contextlib import contextmanager
from copy import copy
import inspect

# Cell
def test_sig(f, b):
    "Test the signature of an object"
    test_eq(str(inspect.signature(f)), b)

# Cell
def _rm_self(sig):
    sigd = dict(sig.parameters)
    sigd.pop('self')
    return sig.replace(parameters=sigd.values())

# Cell
class FixSigMeta(type):
    "A metaclass that fixes the signature on classes that override `__new__`"
    def __new__(cls, name, bases, dict):
        res = super().__new__(cls, name, bases, dict)
        if res.__init__ is not object.__init__: res.__signature__ = _rm_self(inspect.signature(res.__init__))
        return res

# Cell
class PrePostInitMeta(FixSigMeta):
    "A metaclass that calls optional `__pre_init__` and `__post_init__` methods"
    def __call__(cls, *args, **kwargs):
        res = cls.__new__(cls)
        if type(res)==cls:
            if hasattr(res,'__pre_init__'): res.__pre_init__(*args,**kwargs)
            res.__init__(*args,**kwargs)
            if hasattr(res,'__post_init__'): res.__post_init__(*args,**kwargs)
        return res

# Cell
class AutoInit(metaclass=PrePostInitMeta):
    "Same as `object`, but no need for subclasses to call `super().__init__`"
    def __pre_init__(self, *args, **kwargs): super().__init__(*args, **kwargs)

# Cell
class NewChkMeta(FixSigMeta):
    "Metaclass to avoid recreating object passed to constructor"
    def __call__(cls, x=None, *args, **kwargs):
        if not args and not kwargs and x is not None and isinstance(x,cls): return x
        res = super().__call__(*((x,) + args), **kwargs)
        return res

# Cell
class BypassNewMeta(FixSigMeta):
    "Metaclass: casts `x` to this class if it's of type `cls._bypass_type`"
    def __call__(cls, x=None, *args, **kwargs):
        if hasattr(cls, '_new_meta'): x = cls._new_meta(x, *args, **kwargs)
        elif not isinstance(x,getattr(cls,'_bypass_type',object)) or len(args) or len(kwargs):
            x = super().__call__(*((x,)+args), **kwargs)
        if cls!=x.__class__: x.__class__ = cls
        return x

# Cell
def empty2none(p):
    "Replace `Parameter.empty` with `None`"
    return None if p==inspect.Parameter.empty else p

# Cell
def anno_dict(f):
    "`__annotation__ dictionary with `empty` cast to `None`, returning empty if doesn't exist"
    return {k:empty2none(v) for k,v in getattr(f, '__annotations__', {}).items()}

# Cell
def _mk_param(n,d=None): return inspect.Parameter(n, inspect.Parameter.KEYWORD_ONLY, default=d)

# Cell
def use_kwargs_dict(keep=False, **kwargs):
    "Decorator: replace `**kwargs` in signature with `names` params"
    def _f(f):
        sig = inspect.signature(f)
        sigd = dict(sig.parameters)
        k = sigd.pop('kwargs')
        s2 = {n:_mk_param(n,d) for n,d in kwargs.items() if n not in sigd}
        sigd.update(s2)
        if keep: sigd['kwargs'] = k
        f.__signature__ = sig.replace(parameters=sigd.values())
        return f
    return _f

# Cell
def use_kwargs(names, keep=False):
    "Decorator: replace `**kwargs` in signature with `names` params"
    def _f(f):
        sig = inspect.signature(f)
        sigd = dict(sig.parameters)
        k = sigd.pop('kwargs')
        s2 = {n:_mk_param(n) for n in names if n not in sigd}
        sigd.update(s2)
        if keep: sigd['kwargs'] = k
        f.__signature__ = sig.replace(parameters=sigd.values())
        return f
    return _f

# Cell
def delegates(to=None, keep=False, but=None):
    "Decorator: replace `**kwargs` in signature with params from `to`"
    if but is None: but = []
    def _f(f):
        if to is None: to_f,from_f = f.__base__.__init__,f.__init__
        else:          to_f,from_f = to.__init__ if isinstance(to,type) else to,f
        from_f = getattr(from_f,'__func__',from_f)
        to_f = getattr(to_f,'__func__',to_f)
        if hasattr(from_f,'__delwrap__'): return f
        sig = inspect.signature(from_f)
        sigd = dict(sig.parameters)
        k = sigd.pop('kwargs')
        s2 = {k:v for k,v in inspect.signature(to_f).parameters.items()
              if v.default != inspect.Parameter.empty and k not in sigd and k not in but}
        sigd.update(s2)
        if keep: sigd['kwargs'] = k
        else: from_f.__delwrap__ = to_f
        from_f.__signature__ = sig.replace(parameters=sigd.values())
        return f
    return _f

# Cell
def method(f):
    "Mark `f` as a method"
    # `1` is a dummy instance since Py3 doesn't allow `None` any more
    return MethodType(f, 1)

# Cell
def _funcs_kwargs(cls, as_method):
    old_init = cls.__init__
    def _init(self, *args, **kwargs):
        for k in cls._methods:
            arg = kwargs.pop(k,None)
            if arg is not None:
                if as_method: arg = method(arg)
                if isinstance(arg,MethodType): arg = MethodType(arg.__func__, self)
                setattr(self, k, arg)
        old_init(self, *args, **kwargs)
    functools.update_wrapper(_init, old_init)
    cls.__init__ = use_kwargs(cls._methods)(_init)
    if hasattr(cls, '__signature__'): cls.__signature__ = _rm_self(inspect.signature(cls.__init__))
    return cls

# Cell
def funcs_kwargs(as_method=False):
    "Replace methods in `cls._methods` with those from `kwargs`"
    if callable(as_method): return _funcs_kwargs(as_method, False)
    return partial(_funcs_kwargs, as_method=as_method)