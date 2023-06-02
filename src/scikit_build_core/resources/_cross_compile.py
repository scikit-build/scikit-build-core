# Cross compiling activation template

host_name = "${host_name}"

build_time_vars = __import__("${host_name}").build_time_vars.copy()
build_time_vars["SOABI"] = "${SOABI}"
build_time_vars["EXT_SUFFIX"] = "${EXT_SUFFIX}"
