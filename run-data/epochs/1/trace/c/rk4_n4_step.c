/* Reference C for the analytic cost model (HANDOFF 4.5). Never executed by the harness. */
#include <stdint.h>

#define N_STATES 4
#define N_STAGES 4

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

    /* stage 1: c = 1/2 */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        /* 1/2 ~ 1 / 2^1 (exact, csd weight 1) */
        tmp += ((int32_t)hk[0][m] * (int32_t)1) >> 1;
        acc[m] = (int16_t)tmp;                   /* store */
    }
    rk_rhs(acc, k);
    for (m = 0; m < N_STATES; m++) {
        hk[1][m] = (int16_t)(((int32_t)k[m] * (int32_t)h_q) >> 15);
    }

    /* stage 2: c = 1/2 */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        /* 1/2 ~ 1 / 2^1 (exact, csd weight 1) */
        tmp += ((int32_t)hk[1][m] * (int32_t)1) >> 1;
        acc[m] = (int16_t)tmp;                   /* store */
    }
    rk_rhs(acc, k);
    for (m = 0; m < N_STATES; m++) {
        hk[2][m] = (int16_t)(((int32_t)k[m] * (int32_t)h_q) >> 15);
    }

    /* stage 3: c = 1/1 */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        tmp += (int32_t)hk[2][m];
        acc[m] = (int16_t)tmp;                   /* store */
    }
    rk_rhs(acc, k);
    for (m = 0; m < N_STATES; m++) {
        hk[3][m] = (int16_t)(((int32_t)k[m] * (int32_t)h_q) >> 15);
    }

    /* final combination over b */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        /* 1/6 ~ 21845 / 2^17 (approx, csd weight 8) */
        tmp += ((int32_t)hk[0][m] * (int32_t)21845) >> 17;
        /* 1/3 ~ 21845 / 2^16 (approx, csd weight 8) */
        tmp += ((int32_t)hk[1][m] * (int32_t)21845) >> 16;
        /* 1/3 ~ 21845 / 2^16 (approx, csd weight 8) */
        tmp += ((int32_t)hk[2][m] * (int32_t)21845) >> 16;
        /* 1/6 ~ 21845 / 2^17 (approx, csd weight 8) */
        tmp += ((int32_t)hk[3][m] * (int32_t)21845) >> 17;
        y[m] = (int16_t)tmp;                     /* store */
    }
}
