/* Reference C for the analytic cost model (HANDOFF 4.5). Never executed by the harness. */
#include <stdint.h>

#define N_STATES 2
#define N_STAGES 1

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

    /* final combination over b */
    for (m = 0; m < N_STATES; m++) {
        tmp = (int32_t)y[m];                     /* load */
        tmp += (int32_t)hk[0][m];
        y[m] = (int16_t)tmp;                     /* store */
    }
}
