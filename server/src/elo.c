#include "../include/elo.h"
#include <math.h>

void elo_update_pair(int Ra, int Rb, int resultA, int K,
                     int* outRa, int* outRb)
{
    double Sa, Sb;
    if (resultA == 1) {         // A thắng
        Sa = 1.0; Sb = 0.0;
    } else if (resultA == 0) {  // A thua
        Sa = 0.0; Sb = 1.0;
    } else {                    // hòa
        Sa = 0.5; Sb = 0.5;
    }

    double Ea = 1.0 / (1.0 + pow(10.0, (Rb - Ra) / 400.0));
    double Eb = 1.0 / (1.0 + pow(10.0, (Ra - Rb) / 400.0));

    int newRa = (int)(Ra + K * (Sa - Ea) + 0.5);
    int newRb = (int)(Rb + K * (Sb - Eb) + 0.5);

    if (outRa) *outRa = newRa;
    if (outRb) *outRb = newRb;
}
