import { TideInstance, TideService } from '@/app/services/tide.service';
import { Directive, ElementRef, OnDestroy, afterNextRender, inject, input } from '@angular/core';

@Directive({
    selector: '[appSessionCard]',
})
export class SessionCardDirective implements OnDestroy {
    session = input.required<TideInstance>();
    onRefresh = input.required<(id: string, url: string) => void>();
    onRemove = input.required<(id: string) => void>();

    private el = inject(ElementRef);
    private tideService = inject(TideService);
    private observer?: IntersectionObserver;
    private interval?: ReturnType<typeof setInterval>;

    constructor() {
        afterNextRender(() => {
            this.observer = new IntersectionObserver(([entry]) => {
                if (entry.isIntersecting) this.start();
                else this.stop();
            });
            this.observer.observe(this.el.nativeElement);
        });
    }

    private start() {
        if (this.interval) return;
        this.interval = setInterval(() => this.refreshScreenshot(), 10000);
    }

    private stop() {
        clearInterval(this.interval);
        this.interval = undefined;
    }

    private refreshScreenshot() {
        this.tideService.checkInstance(this.session().id).subscribe({
            next: ({ exists }) => {
                if(exists) {
                    if(this.session().tide?.tide_type == "container") {
                        const vnc_url = this.session().vnc_url;
                        if (!vnc_url) return;
                        const base = vnc_url.split('/vnc.html')[0];
                        this.onRefresh()(this.session().id, `${base}/api/get_screenshot?t=${Date.now()}`);
                    }
                }
                else {
                    this.onRemove()(this.session().id);
                }
            },
            error: () => {
                this.onRemove()(this.session().id);
            }
        })
    }

    ngOnDestroy() {
        this.stop();
        this.observer?.disconnect();
    }
}