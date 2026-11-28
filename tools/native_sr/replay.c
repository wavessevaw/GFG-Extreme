// Replay identical SDR input bytes through four scaler kernels. No presentation or FG latency timer.
#include "kfg_vk.h"
#include <stdio.h>
#include <stdlib.h>

static const kfg_vk_image *resolve(void *images,kfg_image_ref r){
    return &((kfg_vk_image *)images)[r.ring];
}

static void add(kfg_plan *plan,int shader,int in,int out,int w,int h,int W,int H){
    kfg_pass *p=kfg_plan_add(plan,shader,kfg_ref(KFG_ROLE_OUTPUT,out,0),"scale");
    p->slots[0]=kfg_ref(KFG_ROLE_COLOR,in,0);
    p->nslots=1;
    p->params.src_size[0]=w; p->params.src_size[1]=h;
    p->params.dst_size[0]=W; p->params.dst_size[1]=H;
    int bx=8,by=8;
    if(shader==KFG_SHADER_WARP){
        p->slots[1]=kfg_ref(KFG_ROLE_COLOR,3,0);
        p->slots[2]=kfg_ref(KFG_ROLE_COLOR,4,0);
        p->nslots=3; bx=32;by=24;
    }
    p->groups[0]=(W+bx-1)/bx; p->groups[1]=(H+by-1)/by;
}

int main(int argc,char **argv){
    if(argc!=5) return 2;
    int w=atoi(argv[1]),h=atoi(argv[2]),W=atoi(argv[3]),H=atoi(argv[4]);
    if(w<1||h<1||W<w||H<h||W>8192||H>8192) return 2;
    kfg_vk vk;
    kfg_vk_image im[5]={0};
    if(kfg_vk_init(&vk,"spv",false)) return 3;
    for(int i=0;i<5;i++)
        if(kfg_vk_image_create(&vk,&im[i],i<3?VK_FORMAT_R8G8B8A8_UNORM:VK_FORMAT_R16G16B16A16_SFLOAT,
                    i>=3?2:i?W:w,i>=3?64:i?H:h)) return 3;
    unsigned char tab[1024];
    FILE *f=fopen("nis-coefficients.bin","rb");
    if(!f)return 3;
    for(int i=3;i<=4;i++) if(fread(tab,1,sizeof(tab),f)!=sizeof(tab)||kfg_vk_upload_raw(&vk,&im[i],tab,sizeof(tab)))return 3;
    fclose(f);
    size_t input=(size_t)w*h*4, output=(size_t)W*H*4;
    unsigned char *bytes=malloc(output);
    if(!bytes)return 3;
    // One input per record on stdin. Four raw RGBA images on stdout in method order.
    while(fread(bytes,1,input,stdin)==input){
        if(kfg_vk_upload_rgba8(&vk,&im[0],bytes))return 3;
        for(int method=0;method<4;method++){
            kfg_plan plan={0};
            if(method==2){
                add(&plan,KFG_SHADER_STATS,0,2,w,h,W,H);
                add(&plan,KFG_SHADER_SELECT,2,1,W,H,W,H);
            }else add(&plan,method==3?KFG_SHADER_WARP:method,0,1,w,h,W,H);
            kfg_vk_begin(&vk);
            if(kfg_vk_record(&vk,&plan,resolve,im)||kfg_vk_submit_wait(&vk))return 3;
            double ns[2]={0};
            if(kfg_vk_pass_times(&vk,ns,2)==plan.n)fprintf(stderr,"dispatch_ms %d %.4f\n",method,(ns[0]+ns[1])*1.e-6);
            if(kfg_vk_download_rgba8(&vk,&im[1],bytes)||fwrite(bytes,1,output,stdout)!=output)return 3;
        }
        fflush(stdout);
    }
    free(bytes);
    for(int i=0;i<5;i++)kfg_vk_image_destroy(&vk,&im[i]);
    kfg_vk_destroy(&vk);
    return ferror(stdin)||ferror(stdout);
}
