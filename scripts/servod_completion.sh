#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# shellcheck disable=SC2207
if [[ -n "${BASH_VERSION:-}" ]]; then
  _servod_comp_source="${BASH_SOURCE[0]}"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
  # shellcheck disable=SC2296
  _servod_comp_source="${(%):-%x}"
  if ! type compdef >/dev/null 2>&1; then
    autoload -Uz compinit && compinit -C
  fi
  autoload -Uz bashcompinit && bashcompinit
else
  return 0
fi
_HDCTOOLS_SCRIPTS_DIR="$(cd -P \
  "$(dirname "$(readlink -f "${_servod_comp_source}")")" >/dev/null 2>&1 \
  && pwd)"
_HDCTOOLS_DATA_DIR=""
if [[ -d "${_HDCTOOLS_SCRIPTS_DIR}/../servo/data" ]]; then
  _HDCTOOLS_DATA_DIR="$(cd -P \
    "${_HDCTOOLS_SCRIPTS_DIR}/../servo/data" >/dev/null 2>&1 && pwd)"
fi
unset _servod_comp_source

_SERVOD_BASE_BOARDS_CACHE=""
_SERVOD_FULL_BOARDS_CACHE=""
_servod_get_boards() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  [[ -n "${_HDCTOOLS_DATA_DIR}" && -d "${_HDCTOOLS_DATA_DIR}" ]] || return 0
  local prefix="${1:-}"

  if [[ "${prefix}" == *_* ]]; then
    if [[ -z "${_SERVOD_FULL_BOARDS_CACHE}" ]]; then
      local f b name
      local names=()
      for f in "${_HDCTOOLS_DATA_DIR}"/servo_*_overlay.xml; do
        [[ -f "${f}" ]] || continue
        b="${f##*/servo_}"
        name="${b%_overlay.xml}"
        if [[ "${name}" == fpmcu_dev_board_*common* ]]; then
          continue
        fi
        names+=("${name}")
      done
      if [[ ${#names[@]} -gt 0 ]]; then
        _SERVOD_FULL_BOARDS_CACHE="$(printf '%s\n' "${names[@]}" | sort -u)"
      fi
    fi
    echo "${_SERVOD_FULL_BOARDS_CACHE}"
  else
    if [[ -z "${_SERVOD_BASE_BOARDS_CACHE}" ]]; then
      local f b name
      local boards=()
      for f in "${_HDCTOOLS_DATA_DIR}"/servo_*_overlay.xml; do
        [[ -f "${f}" ]] || continue
        b="${f##*/servo_}"
        name="${b%_overlay.xml}"
        if [[ "${name}" == fpmcu_dev_board_* ]]; then
          if [[ "${name}" != *common* ]]; then
            boards+=("fpmcu_dev_board")
          fi
        else
          boards+=("${name%%_*}")
        fi
      done
      if [[ ${#boards[@]} -gt 0 ]]; then
        _SERVOD_BASE_BOARDS_CACHE="$(printf '%s\n' "${boards[@]}" | sort -u)"
      fi
    fi
    echo "${_SERVOD_BASE_BOARDS_CACHE}"
  fi
}

_servod_get_models() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  [[ -n "${_HDCTOOLS_DATA_DIR}" && -d "${_HDCTOOLS_DATA_DIR}" ]] || return 0
  local board="${1:-}"
  local f b model
  local models=()
  if [[ -n "${board}" ]]; then
    for f in "${_HDCTOOLS_DATA_DIR}"/servo_"${board}"_*_overlay.xml; do
      [[ -f "${f}" ]] || continue
      b="${f##*/servo_"${board}"_}"
      model="${b%_overlay.xml}"
      models+=("${model}")
    done
  else
    for f in "${_HDCTOOLS_DATA_DIR}"/servo_*_*_overlay.xml; do
      [[ -f "${f}" ]] || continue
      b="${f##*/servo_}"
      b="${b%_overlay.xml}"
      model="${b#*_}"
      models+=("${model}")
    done
  fi
  if [[ ${#models[@]} -gt 0 ]]; then
    printf '%s\n' "${models[@]}" | sort -u
  fi
}

_SERVOD_XMLS_CACHE=""
_servod_get_xmls() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  [[ -n "${_HDCTOOLS_DATA_DIR}" && -d "${_HDCTOOLS_DATA_DIR}" ]] || return 0
  if [[ -z "${_SERVOD_XMLS_CACHE}" ]]; then
    local f b
    local xmls=()
    for f in "${_HDCTOOLS_DATA_DIR}"/*.xml; do
      [[ -f "${f}" ]] || continue
      b="${f##*/}"
      xmls+=("${b}")
    done
    if [[ ${#xmls[@]} -gt 0 ]]; then
      _SERVOD_XMLS_CACHE="$(printf '%s\n' "${xmls[@]}" | sort -u)"
    fi
  fi
  echo "${_SERVOD_XMLS_CACHE}"
}

_SERVOD_CONTROLS_CACHE=""
_servod_get_controls() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  [[ -n "${_HDCTOOLS_DATA_DIR}" && -d "${_HDCTOOLS_DATA_DIR}" ]] || return 0
  if [[ -z "${_SERVOD_CONTROLS_CACHE}" ]]; then
    _SERVOD_CONTROLS_CACHE="$(sed -n \
      's/.*<name>\([^<.]*\)<\/name>.*/\1/p' \
      "${_HDCTOOLS_DATA_DIR}"/*.xml 2>/dev/null | sort -u)"
  fi
  echo "${_SERVOD_CONTROLS_CACHE}"
}

_servod_get_serials() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local dev vendor
  for dev in /sys/bus/usb/devices/*; do
    [[ -e "${dev}" ]] || continue
    if [[ -f "${dev}/idVendor" && -f "${dev}/serial" ]]; then
      vendor="$(cat "${dev}/idVendor" 2>/dev/null)"
      if [[ "${vendor}" == "18d1" ]]; then
        cat "${dev}/serial" 2>/dev/null
      fi
    fi
  done
}

_servod_get_containers() {
  docker ps --filter "name=docker_servod" --format "{{.Names}}" \
    2>/dev/null | sed 's/-docker_servod$//'
}

_servod_get_ports() {
  docker ps --filter "name=docker_servod" --format "{{.Ports}}" \
    2>/dev/null | grep -oE '[0-9]+->9999' | cut -d- -f1 | sort -u
}

_servod_find_board() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local i word
  for ((i = 1; i < COMP_CWORD; i++)); do
    word="${COMP_WORDS[i]}"
    if [[ "${word}" == -b=* || "${word}" == --board=* ]]; then
      echo "${word#*=}"
      return 0
    fi
    if [[ "${word}" == "-b" || "${word}" == "--board" ]]; then
      if (( i + 1 < COMP_CWORD )); then
        if [[ "${COMP_WORDS[i+1]}" == "=" ]]; then
          if (( i + 2 < COMP_CWORD )); then
            echo "${COMP_WORDS[i+2]}"
            return 0
          fi
        else
          echo "${COMP_WORDS[i+1]}"
          return 0
        fi
      fi
    fi
  done
}

_servod_has_double_dash() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local i
  for ((i = 1; i < COMP_CWORD; i++)); do
    if [[ "${COMP_WORDS[i]}" == "--" ]]; then
      return 0
    fi
  done
  return 1
}

_servod_parse_opt_val() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  opt=""
  val=""
  eq_prefix=""

  if [[ "${cur}" == "=" ]]; then
    opt="${prev}"
    val=""
    eq_prefix=""
  elif [[ "${prev}" == "=" && "${COMP_CWORD}" -ge 2 ]]; then
    opt="${COMP_WORDS[COMP_CWORD-2]}"
    val="${cur}"
    eq_prefix=""
  elif [[ "${cur}" == -*=* ]]; then
    opt="${cur%%=*}"
    val="${cur#*=}"
    eq_prefix="${opt}="
  else
    opt="${prev}"
    val="${cur}"
    eq_prefix=""
  fi
}

_servod_reply_words() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local words="$1"
  local val="$2"
  local eq_prefix="$3"
  local matches=()
  local w
  for w in ${words}; do
    if [[ -z "${val}" || "${w}" == "${val}"* ]]; then
      matches+=("${eq_prefix}${w}")
    fi
  done
  COMPREPLY=("${matches[@]}")
}

_servod_reply_files() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local val="$1"
  local eq_prefix="$2"
  local type_flag="${3:--f}"
  # shellcheck disable=SC2207
  COMPREPLY=( $(compgen "${type_flag}" -- "${val}") )
  if [[ -n "${eq_prefix}" && ${#COMPREPLY[@]} -gt 0 ]]; then
    COMPREPLY=( "${COMPREPLY[@]/#/${eq_prefix}}" )
  fi
}

_servod_start() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  local opt val eq_prefix
  _servod_parse_opt_val

  if ! _servod_has_double_dash; then
    case "${opt}" in
      -c|--channel)
        _servod_reply_words \
          "local latest fission-latest beta release" "${val}" "${eq_prefix}"
        return 0
        ;;
      -b|--board)
        _servod_reply_words \
          "$(_servod_get_boards "${val}")" "${val}" "${eq_prefix}"
        return 0
        ;;
      -m|--model)
        local board
        board="$(_servod_find_board)"
        _servod_reply_words \
          "$(_servod_get_models "${board}")" "${val}" "${eq_prefix}"
        return 0
        ;;
      -s|--serial)
        _servod_reply_words \
          "$(_servod_get_serials)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -f|--follow)
        if [[ "${cur}" != "=" && "${prev}" != "=" && \
              "${cur}" != -*=* && "${cur}" == -* ]]; then
          : # Fall through to opts completion below
        else
          _servod_reply_words \
            "INFO WARNING DEBUG" "${val}" "${eq_prefix}"
          return 0
        fi
        ;;
      --mount|--token_db|--logs|--dump-xml)
        _servod_reply_files "${val}" "${eq_prefix}" -f
        return 0
        ;;
      -n|--container_name)
        # Creating a new container: do not suggest existing containers.
        return 0
        ;;
      -p|--port|--docker-label)
        return 0
        ;;
    esac

    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      local opts=(
        -h --help
        -c --channel
        --docker-label
        -b --board
        -m --model
        -s --serial
        -n --container_name
        -t --run_tests --no-run_tests
        -d --sleep --no-sleep
        --mount
        -p --port
        -f --follow
        -v --verbose --no-verbose
        --debug --no-debug
        --allow_offline --no-allow_offline
        --force_update --no-force_update
        --token_db
        --logs
        --dump-xml
        --noboard --no-noboard
        --nomodel --no-nomodel
        --
      )
      _servod_reply_words "${opts[*]}" "${cur}" ""
    fi
  else
    case "${opt}" in
      -c|--config)
        _servod_reply_words \
          "$(_servod_get_xmls)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -b|--board)
        _servod_reply_words \
          "$(_servod_get_boards "${val}")" "${val}" "${eq_prefix}"
        return 0
        ;;
      -m|--model)
        local board
        board="$(_servod_find_board)"
        _servod_reply_words \
          "$(_servod_get_models "${board}")" "${val}" "${eq_prefix}"
        return 0
        ;;
      -s|--serialname)
        _servod_reply_words \
          "$(_servod_get_serials)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -p|--port)
        return 0
        ;;
    esac

    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      local post_opts=(
        -h --help
        -c --config
        -b --board
        -m --model
        -s --serialname
        -p --port
        --debug
        --allow-dual-v4
        --recovery_mode
      )
      _servod_reply_words "${post_opts[*]}" "${cur}" ""
    fi
  fi
}

_servod_stop() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  local opt val eq_prefix
  _servod_parse_opt_val

  case "${opt}" in
    -n|--container_name)
      _servod_reply_words \
        "$(_servod_get_containers)" "${val}" "${eq_prefix}"
      return 0
      ;;
    -p|--port)
      _servod_reply_words \
        "$(_servod_get_ports)" "${val}" "${eq_prefix}"
      return 0
      ;;
  esac

  if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
    _servod_reply_words \
      "-h --help -n --container_name -p --port" "${cur}" ""
  fi
}

_servod_dut_control() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  local opt val eq_prefix
  _servod_parse_opt_val

  if ! _servod_has_double_dash; then
    case "${opt}" in
      -n|--container_name)
        _servod_reply_words \
          "$(_servod_get_containers)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -p|--port)
        _servod_reply_words \
          "$(_servod_get_ports)" "${val}" "${eq_prefix}"
        return 0
        ;;
    esac
    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      _servod_reply_words \
        "-h --help -n --container_name -p --port --" "${cur}" ""
    fi
  else
    case "${opt}" in
      -s|--serialname)
        _servod_reply_words \
          "$(_servod_get_serials)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -p|--port)
        _servod_reply_words \
          "$(_servod_get_ports)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -i|--info|-r|--repeat|-t|--time|-v|--verbose)
        ;;
    esac

    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      if [[ "${cur}" == -* ]]; then
        local post_flags=(
          -h --help -i --info -r --repeat -t --time -v --verbose
          -p --port -s --serialname
        )
        _servod_reply_words "${post_flags[*]}" "${cur}" ""
      else
        _servod_reply_words "$(_servod_get_controls)" "${cur}" ""
      fi
    fi
  fi
}

_servod_dut_power() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  local opt val eq_prefix
  _servod_parse_opt_val

  if ! _servod_has_double_dash; then
    case "${opt}" in
      -n|--container_name)
        _servod_reply_words \
          "$(_servod_get_containers)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -p|--port)
        _servod_reply_words \
          "$(_servod_get_ports)" "${val}" "${eq_prefix}"
        return 0
        ;;
    esac
    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      _servod_reply_words \
        "-h --help -n --container_name -p --port --" "${cur}" ""
    fi
  else
    case "${opt}" in
      -o|--outdir)
        _servod_reply_files "${val}" "${eq_prefix}" -d
        return 0
        ;;
      -s|--serialname)
        _servod_reply_words \
          "$(_servod_get_serials)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -p|--port)
        _servod_reply_words \
          "$(_servod_get_ports)" "${val}" "${eq_prefix}"
        return 0
        ;;
    esac

    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      local post_flags=(
        -h --help -t --time -f --fast --vbat-rate --ina-rate
        --no-vbat --no-ina --no-display --save-logs --save-raw-data
        --save-summary -o --outdir -m --message -s --serialname -p --port
      )
      _servod_reply_words "${post_flags[*]}" "${cur}" ""
    fi
  fi
}

_servod_servodtool() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  local opt val eq_prefix
  _servod_parse_opt_val

  if ! _servod_has_double_dash; then
    case "${opt}" in
      -c|--updater_channel)
        _servod_reply_words \
          "local latest beta release" "${val}" "${eq_prefix}"
        return 0
        ;;
      -n|--name)
        _servod_reply_words \
          "$(_servod_get_containers)" "${val}" "${eq_prefix}"
        return 0
        ;;
    esac
    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      local pre_flags=(
        -h --help -c --updater_channel -n --name
        --force_update --no-force_update --
      )
      _servod_reply_words "${pre_flags[*]}" "${cur}" ""
    fi
  else
    case "${opt}" in
      -s)
        _servod_reply_words \
          "$(_servod_get_serials)" "${val}" "${eq_prefix}"
        return 0
        ;;
    esac

    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      local after_dd=0
      local subcmd=""
      local i
      for ((i = 1; i < COMP_CWORD; i++)); do
        if [[ "${COMP_WORDS[i]}" == "--" ]]; then
          after_dd=1
          continue
        fi
        if (( after_dd )); then
          if [[ "${COMP_WORDS[i]}" == "instance" || \
                "${COMP_WORDS[i]}" == "device" ]]; then
            subcmd="${COMP_WORDS[i]}"
            break
          fi
        fi
      done

      case "${subcmd}" in
        instance)
          _servod_reply_words \
            "show-all wait-for-active rebuild stop -h --help" "${cur}" ""
          ;;
        device)
          _servod_reply_words \
            "-s usb-path reboot power-cycle watchdog -h --help" "${cur}" ""
          ;;
        *)
          _servod_reply_words "instance device -h --help" "${cur}" ""
          ;;
      esac
    fi
  fi
}

_servod_updater() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  local prev="${COMP_WORDS[COMP_CWORD-1]}"

  local opt val eq_prefix
  _servod_parse_opt_val

  if ! _servod_has_double_dash; then
    case "${opt}" in
      -c|--updater_channel)
        _servod_reply_words \
          "local latest beta release" "${val}" "${eq_prefix}"
        return 0
        ;;
      -n|--name)
        _servod_reply_words \
          "$(_servod_get_containers)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -f|--file)
        _servod_reply_files "${val}" "${eq_prefix}" -f
        return 0
        ;;
    esac
    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      local pre_flags=(
        -h --help -c --updater_channel -n --name -f --file
        --force_update --no-force_update --
      )
      _servod_reply_words "${pre_flags[*]}" "${cur}" ""
    fi
  else
    case "${opt}" in
      -b|--board)
        local updater_boards="servo_v4 servo_v4p1 servo_micro c2d2 sweetberry"
        updater_boards="${updater_boards} ccd_cr50 ccd_ti50"
        _servod_reply_words "${updater_boards}" "${val}" "${eq_prefix}"
        return 0
        ;;
      -c|--channel)
        _servod_reply_words \
          "default recovery prev alpha" "${val}" "${eq_prefix}"
        return 0
        ;;
      -s|--serialno)
        _servod_reply_words \
          "$(_servod_get_serials)" "${val}" "${eq_prefix}"
        return 0
        ;;
      -f|--file)
        _servod_reply_files "${val}" "${eq_prefix}" -f
        return 0
        ;;
    esac

    if [[ "${cur}" != "=" && "${prev}" != "=" && "${cur}" != -*=* ]]; then
      local post_flags=(
        -h --help -b --board -s --serialno -c --channel
        -f --file --force -v --verbose -r --reboot
      )
      _servod_reply_words "${post_flags[*]}" "${cur}" ""
    fi
  fi
}

_servod_ps() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  _servod_reply_words "-h --help" "${cur}" ""
}

_servod_build() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  _servod_reply_words "multi cq" "${cur}" ""
}

_servod_tests() {
  [[ -n "${ZSH_VERSION:-}" ]] && emulate -L sh
  local cur="${COMP_WORDS[COMP_CWORD]}"
  if [[ "${cur}" == -* ]]; then
    _servod_reply_words "--fast" "${cur}" ""
  else
    _servod_reply_files "${cur}" "" -f
    if [[ -z "${cur}" || "--fast" == "${cur}"* ]]; then
      COMPREPLY+=( "--fast" )
    fi
  fi
}

complete -F _servod_start start-servod servod-start
complete -F _servod_stop stop-servod servod-stop
complete -F _servod_dut_control dut-control
complete -F _servod_dut_power dut-power
complete -F _servod_servodtool servodtool
complete -F _servod_updater servo_updater
complete -F _servod_ps servod-ps
complete -F _servod_build build-servod
complete -F _servod_tests run-servod-tests
