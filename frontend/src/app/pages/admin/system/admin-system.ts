import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, model, signal } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { SkeletonModule } from 'primeng/skeleton';
import { SystemInfo, SystemService } from '../../../services/system.service';

@Component({
    selector: 'app-admin-system',
    imports: [CommonModule, CardModule, SkeletonModule, ButtonModule, TranslateModule],
    templateUrl: './admin-system.html'
})
export class AdminSystem implements OnInit {
    private systemService = inject(SystemService);

    loading = signal(true);
    info = signal<SystemInfo>({
        success: true,
        system: {
            hostname: "",
            os: ""
        },
        version: {
            docker: "",
            tidalcase: "",
            nginx: "",
            python: ""
        }
    });

    ngOnInit() { this.load(); }

    load() {
        this.loading.set(true);
        this.systemService.getSystemInfo().subscribe({
            next: (res) => { this.info.set(res); this.loading.set(false); },
            error: () => { this.loading.set(false); }
        });
    }
}
