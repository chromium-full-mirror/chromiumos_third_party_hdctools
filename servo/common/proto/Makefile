# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

include $(HDCTOOLS_DIR)/defs/definitions.mk
include $(HDCTOOLS_DIR)/defs/utilities.mk

PYTHON_SRC	= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.py))
PYTHON_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(PYTHON_SRC))
PROTOS	= $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.proto))
PROTO_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(PROTOS))
TEXTPROTO_SRC = $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.textproto))
TEXTPROTO_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(TEXTPROTO_SRC))


$(THIS_BUILD_DIR)/%.textproto: $(HDCTOOLS_SOURCE_DIR)/%.textproto
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(THIS_BUILD_DIR)/%.proto: $(HDCTOOLS_SOURCE_DIR)/%.proto
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

$(THIS_BUILD_DIR)/%.py: $(HDCTOOLS_SOURCE_DIR)/%.py
	$(MESSAGE) "Copying $(notdir $@)"
	$(CP) $< $@

ver:
	python3 $(HDCTOOLS_DIR)/servo/grpc.py;


all: 		ver $(PYTHON_DST) $(TEXTPROTO_DST)
install:
