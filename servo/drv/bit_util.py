# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Utility functions for bitfield manipulations."""


def extract_bitfield(field, mask, shift):
    """Extract bits of interest from |field|.

    Note: mask should be defined assuming that the shift will bring the bits
          of interest to the least significant bit first e.g. if the user
          cares about bits 5-7 they would supply
            shift -> 4
            mask -> 0xf
          to extract 4 bits of data after shifting the content 4 bits to the right

    Args:
      field: int, entire bitfield content e.g. from a register
      mask: int, mask identifying the bits of interest
      shift: int, right-shift to bring bits of interest to least significant bit

    Returns:
      boi: int, the bits of interest
    """
    return (field >> shift) & mask


def set_bitfield(field, mask, shift, content):
    """Set bits defined by |mask| and |shift| in |field| to |content|.

    Note: |mask| is used to both zero out the current value inside
          |field| (|mask| << |shift|) and to make sure that |content| is only
          applied to the bits of interest by &'ing it with the mask.
          Make sure that the |content| value and |mask| value match.

    Args:
      field: int, entire bitfield content e.g. from a register
      mask: int, mask identifying the bits of interest
      shift: int, left-shift to bring mask and value to the correct bit location
             in |field|

    Returns:
      field: int, modified field after the above operation
    """
    mask <<= shift
    content = (content << shift) & mask
    # First zero out the current content with the mask, then set with content.
    new_field = (field & ~mask) | content
    return new_field
