#!/bin/bash

BASEDIR=$(dirname $0)

exec $(cat $BASEDIR/.jackdrc)
