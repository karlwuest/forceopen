#include <iostream>
#include <fstream>
#include <set>
#include "pin.H"

ofstream OutFile;
ifstream ModFile;
set<string> modules;


KNOB<string> KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool",
    "o", "branchtrace.out", "specify output file name");

KNOB<string> KnobModuleFile(KNOB_MODE_WRITEONCE, "pintool",
    "m", "modules", "specify file name containing the modules to instrument (if file is empty, the names of loaded modules will be written to this file)");


/* called before every branch, outputs the name of the image and the offset of the instruction and the branch target to the start address */
VOID branch(long long ip, bool branch_taken, long long target_addr, long long fallthrough_addr, long long start_addr)
{
    PIN_LockClient();
    if (branch_taken){
        OutFile << IMG_Name(IMG_FindByAddress(ip)) << ' ' << ip - start_addr << ' ' << target_addr - start_addr << endl;
    } else {
        OutFile << IMG_Name(IMG_FindByAddress(ip)) << ' ' << ip - start_addr << ' ' << fallthrough_addr - start_addr << endl;
    }
    PIN_UnlockClient();
}


// Pin calls this function every time a new instruction is encountered
/*
VOID Instruction(INS ins, VOID *v)
{
    if (INS_IsDirectBranch(ins)) {
        INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR) branch, IARG_INST_PTR, IARG_ADDRINT, INS_DirectBranchOrCallTargetAddress(ins), IARG_END);
    }
}
*/


VOID ImageLoad(IMG img, VOID *v)
 {
    if (modules.empty()) {
        /* output the name of the loaded module and return */
        ofstream ModOut;
        ModOut.open(KnobModuleFile.Value().c_str(), ios_base::app);
        ModOut << IMG_Name(img) << endl;
        return;
    } else if (modules.find(IMG_Name(img)) == modules.end()) {
        /* don't output information about this module */
        return;
    }

    /* loop through all instructions */
    for (SEC sec = IMG_SecHead(img); SEC_Valid(sec); sec = SEC_Next(sec)) {
        for (RTN rtn = SEC_RtnHead(sec); RTN_Valid(rtn); rtn = RTN_Next(rtn)) {
            RTN_Open(rtn);
            for (INS ins = RTN_InsHead(rtn); INS_Valid(ins); ins = INS_Next(ins)) {
                if (INS_IsDirectBranch(ins) && INS_HasFallThrough(ins)) {
                    /* insert instrumenting function */
                    //INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR) branch, IARG_ADDRINT, INS_Address(ins), IARG_ADDRINT, INS_DirectBranchOrCallTargetAddress(ins), IARG_ADDRINT, IMG_LowAddress(img), IARG_END);
                    INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR) branch, IARG_INST_PTR, IARG_BRANCH_TAKEN, IARG_BRANCH_TARGET_ADDR, IARG_FALLTHROUGH_ADDR, IARG_ADDRINT, IMG_LowAddress(img), IARG_END);
                }
            }
            RTN_Close(rtn);
        }
    }
 }

// This function is called when the application exits
VOID Fini(INT32 code, VOID *v)
{
    OutFile.close();
}

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage()
{
    cerr << "This tool traces the branches taken in a program" << endl;
    cerr << endl << KNOB_BASE::StringKnobSummary() << endl;
    return -1;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */
/*   argc, argv are the entire command line: pin -t <toolname> -- ...    */
/* ===================================================================== */

int main(int argc, char * argv[])
{
    // Initialize pin
    if (PIN_Init(argc, argv)) return Usage();

    ModFile.open(KnobModuleFile.Value().c_str());
    string mod;
    while (ModFile >> mod) {
        modules.insert(mod);
    }
    ModFile.close();

    OutFile.open(KnobOutputFile.Value().c_str());
    OutFile.setf(ios::showbase);

    // Register Instruction to be called to instrument instructions
    //INS_AddInstrumentFunction(Instruction, 0);

    // Register ImageLoad to be called at every module load
    IMG_AddInstrumentFunction(ImageLoad, 0);

    // Register Fini to be called when the application exits
    PIN_AddFiniFunction(Fini, 0);

    // Start the program, never returns
    PIN_StartProgram();

    return 0;
}

