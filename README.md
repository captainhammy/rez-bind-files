# Rez Bind Files

This repo contains custom bind modules for `rez`.

## Usage

To use any files contained in this repo they must be located in a place that `rez-bind` can find. `rez` accomplishes
this using the [bind_module_path](https://rez.readthedocs.io/en/stable/configuring_rez.html#bind_module_path). 

You can add the location of this repo to the `bind_module_path` inside your `rezconfig.py` file or by using the
`REZ_BIND_MODULE_PATH` variable.
