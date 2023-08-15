# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Collection of helpers functions to check against system config."""


def is_map(config, sname):
    """Ensure that in |config| there is a map called |sname|."""
    return config.is_map(sname)


def map_key_to_val(config, smap, key, val):
    """Ensure that in |config| the |smap| has |key| mapping to |val|."""
    mparams = config.lookup_map_params(smap)
    if key not in mparams:
        return False
    return mparams[key] == val


def is_control(config, cname):
    """Check in |config| there is a ctrl called |cname|."""
    return config.is_control(cname)


def ctrl_drv(config, cname, drv):
    """Check in |config|, ctrl |cname| has drv |drv| on get & set."""
    return ctrl_drv_get(config, cname, drv) and ctrl_drv_set(config, cname, drv)


def ctrl_drv_get(config, cname, drv):
    """Check in |config|, ctrl |cname| has drv |drv| on get."""
    return ctrl_param_get(config, cname, "drv", drv)


def ctrl_drv_set(config, cname, drv):
    """Check in |config|, ctrl |cname| has drv |drv| on set."""
    return ctrl_param_set(config, cname, "drv", drv)


def ctrl_interface(config, cname, interface):
    """Check in |config|, ctrl |cname| has interface |interface| on get & set."""
    return ctrl_interface_get(config, cname, interface) and ctrl_interface_set(
        config, cname, interface
    )


def ctrl_interface_get(config, cname, interface):
    """Check in |config|, ctrl |cname| has interface |interface| on get."""
    return ctrl_param_get(config, cname, "interface", interface)


def ctrl_interface_set(config, cname, interface):
    """Check in |config|, ctrl |cname| has interface |interface| on set."""
    return ctrl_param_set(config, cname, "interface", interface)


def ctrl_subtype(config, cname, subtype):
    """Check in |config|, ctrl |cname| has subtype |subtype| on get & set."""
    return ctrl_subtype_get(config, cname, subtype) and ctrl_subtype_set(
        config, cname, subtype
    )


def ctrl_subtype_get(config, cname, subtype):
    """Check in |config|, ctrl |cname| has subtype |subtype| on get."""
    return ctrl_param_get(config, cname, "subtype", subtype)


def ctrl_subtype_set(config, cname, subtype):
    """Check in |config|, ctrl |cname| has subtype |subtype| on set."""
    return ctrl_param_set(config, cname, "subtype", subtype)


def ctrl_init(config, cname, init):
    """Check in |config|, ctrl |cname| has init |init| on get & set."""
    return ctrl_init_get(config, cname, init) and ctrl_init_set(config, cname, init)


def ctrl_init_get(config, cname, init):
    """Check in |config|, ctrl |cname| has init |init| on get."""
    return ctrl_param_get(config, cname, "init", init)


def ctrl_init_set(config, cname, init):
    """Check in |config|, ctrl |cname| has init |init| on set."""
    return ctrl_param_set(config, cname, "init", init)


# The following functions are generic param lookups - feed
# a parameter name (pname) and parameter value (pval)


def ctrl_param(config, cname, pname, pval):
    """Check in |config|, ctrl |cname| has |pname| as |pval| on get & set."""
    return ctrl_param_get(config, cname, pname, pval) and ctrl_param_set(
        config, cname, pname, pval
    )


def ctrl_param_get(config, cname, pname, pval):
    """Check in |config|, ctrl |cname| has |pname| as |pval| on get."""
    cparams, _unused = config.lookup_control_params(cname)
    # NOTE: passing None means checking that that the param does not exist
    if pname not in cparams:
        return pval is None
    return cparams[pname] == pval


def ctrl_param_set(config, cname, pname, pval):
    """Check in |config|, ctrl |cname| has |pname| as |pval| on set."""
    _unused, cparams = config.lookup_control_params(cname)
    # NOTE: passing None means checking that that the param does not exist
    if pname not in cparams:
        return pval is None
    return cparams[pname] == pval
