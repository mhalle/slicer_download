#!/bin/sh

LOCALPATH=$(cd "$(dirname $0)"; pwd -P)
exec /usr/bin/env python "$LOCALPATH" "$@"
