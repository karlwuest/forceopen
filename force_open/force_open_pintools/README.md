* branchtrace is a pintool to output the source and target address of the branches of the instrumented program
* hijack is a pintool to modify the execution of a program, according to the branches input file
* each branch (in the output of branchtrace / input of hijack) has the form:

    `<module_name> <source_offset> <target_offset>`

where the offsets are the offsets from the actual addresses to the base address of the module at load time

Instructions:

* Download Pin (https://software.intel.com/en-us/articles/pintool-downloads)
* unpack to ../
* rename the newly created directory to 'pin'
* run `make`
* run the pintool with:

`../pin/pin -injection child -t obj-intel64/<pintool_name>.so -- <program to instrument> <program arguments>`

Pin Version used: pin-2.14-71313-gcc.4.4.7-linux

