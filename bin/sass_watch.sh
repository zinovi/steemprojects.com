#!/bin/bash
# watch sass files and generate new css once modified
# usage from project root directory: ./bin/sass_watch.sh
sass --watch static/scss:static/css
