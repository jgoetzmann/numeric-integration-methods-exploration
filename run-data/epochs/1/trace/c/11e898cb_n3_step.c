/* Reference C for the analytic cost model (HANDOFF 4.5). Never executed by the harness. */
#include <stdint.h>

#define N_STATES 3
#define N_STAGES 3

/* Q15 derivative dy = f(y), supplied by the application. */
extern void rk_rhs(const int16_t *y, int16_t *dy);

void rk_step(int16_t *y, int16_t h_q)
{
    int16_t hk[N_STAGES][N_STATES];
    int16_t acc[N_STATES];
    int16_t k[N_STATES];
    int32_t tmp;
    int m;

    /* stage 0: c = 0/1 */
    /* row of A is all zero: stage input is y itself */
    rk_rhs(y, k);
    for (m = 0; m < N_STATES; m++) {
        hk[0][m] = (int16_t)(((int32_t)k[m] * (int32_t)h_q) >> 15);
    }

    /* stage 1: c = 13/16 */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        /* 13/16 ~ 13 / 2^4 (exact, csd weight 3) */
        tmp += ((int32_t)hk[0][m] * (int32_t)13) >> 4;
        acc[m] = (int16_t)tmp;                   /* store */
    }
    rk_rhs(acc, k);
    for (m = 0; m < N_STATES; m++) {
        hk[1][m] = (int16_t)(((int32_t)k[m] * (int32_t)h_q) >> 15);
    }

    /* stage 2: c = 1/2 */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        /* 5/32 ~ 5 / 2^5 (exact, csd weight 2) */
        tmp += ((int32_t)hk[0][m] * (int32_t)5) >> 5;
        /* 11/32 ~ 11 / 2^5 (exact, csd weight 3) */
        tmp += ((int32_t)hk[1][m] * (int32_t)11) >> 5;
        acc[m] = (int16_t)tmp;                   /* store */
    }
    rk_rhs(acc, k);
    for (m = 0; m < N_STATES; m++) {
        hk[2][m] = (int16_t)(((int32_t)k[m] * (int32_t)h_q) >> 15);
    }

    /* final combination over b */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        tmp += (int32_t)hk[2][m];
        y[m] = (int16_t)tmp;                     /* store */
    }
}
