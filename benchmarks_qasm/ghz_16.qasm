OPENQASM 2.0;
include "qelib1.inc";
qreg q3[16];
h q3[1];
h q3[2];
h q3[3];
h q3[4];
h q3[5];
h q3[6];
h q3[7];
h q3[8];
h q3[9];
h q3[10];
h q3[11];
h q3[12];
h q3[13];
h q3[14];
h q3[15];
cx q3[15],q3[0];
cx q3[14],q3[0];
cx q3[13],q3[0];
cx q3[12],q3[0];
cx q3[11],q3[0];
cx q3[10],q3[0];
cx q3[9],q3[0];
cx q3[8],q3[0];
cx q3[7],q3[0];
cx q3[6],q3[0];
cx q3[5],q3[0];
cx q3[4],q3[0];
cx q3[3],q3[0];
cx q3[2],q3[0];
cx q3[1],q3[0];
h q3[0];
h q3[1];
h q3[2];
h q3[3];
h q3[4];
h q3[5];
h q3[6];
h q3[7];
h q3[8];
h q3[9];
h q3[10];
h q3[11];
h q3[12];
h q3[13];
h q3[14];
h q3[15];
