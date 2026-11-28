// Emit SDR constants from the same upstream setup function used in Gamescope.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include "NVIDIAImageScaling/NIS/NIS_Config.h"
int main(){
    NISConfig c{};
    if (!NVScalerUpdateConfig(c,NIS_STRENGTH,0,0,800,500,800,500,0,0,1280,800,1280,800)) return 1;
#define EMIT(name) printf("const float " #name " = %.9ef;\n",double(c.name))
    EMIT(kDetectRatio); EMIT(kDetectThres); EMIT(kMinContrastRatio); EMIT(kRatioNorm);
    EMIT(kContrastBoost); EMIT(kEps); EMIT(kSharpStartY); EMIT(kSharpScaleY);
    EMIT(kSharpStrengthMin); EMIT(kSharpStrengthScale); EMIT(kSharpLimitMin); EMIT(kSharpLimitScale);
    FILE *f=fopen("nis-coefficients.bin","wb"); if(!f) return 1;
    if(fwrite(coef_scale_fp16,1,sizeof(coef_scale_fp16),f)!=sizeof(coef_scale_fp16) ||
       fwrite(coef_usm_fp16,1,sizeof(coef_usm_fp16),f)!=sizeof(coef_usm_fp16)) return 1;
    return fclose(f)!=0;
}
