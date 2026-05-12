import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { CheckboxModule } from 'primeng/checkbox';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { TranslateService } from '@ngx-translate/core';
import { Agent, AgentService } from '../../../services/agent.service';

@Component({
    selector: 'app-admin-agents',
    standalone: true,
    imports: [FormsModule, TableModule, ButtonModule, TagModule, SkeletonModule, CardModule, ToastModule, ConfirmDialogModule, DialogModule, InputTextModule, CheckboxModule, SelectModule, TranslateModule, TooltipModule],
    providers: [MessageService, ConfirmationService],
    templateUrl: './admin-agents.html',
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminAgents implements OnInit {
    private readonly service = inject(AgentService);
    private readonly messageService = inject(MessageService);
    private readonly confirmationService = inject(ConfirmationService);
    private readonly translate = inject(TranslateService);

    readonly loading = signal(true);
    readonly saving = signal(false);
    readonly testing = signal(false);
    readonly agents = signal<Agent[]>([]);
    readonly joinToken = signal('');
    readonly showDialog = signal(false);
    readonly editingAgent = signal<Partial<Agent>>({});
    readonly testResult = signal<{ success: boolean; message: string } | null>(null);
    readonly tokenCopied = signal(false);

    readonly pruneOptions = [
        { label: 'Off', value: 'off' },
        { label: 'Normal (dangling only)', value: 'normal' },
        { label: 'Aggressive (non-app images)', value: 'aggressive' },
    ];

    ngOnInit(): void {
        this.load();
    }

    load() {
        this.loading.set(true);
        this.service.getAgents().subscribe({
            next: (res) => {
                this.agents.set(res.agents || []);
                if (res.join_token) this.joinToken.set(res.join_token);
                this.loading.set(false);
            },
            error: () => { this.loading.set(false); },
        });
    }

    copyToken() {
        navigator.clipboard.writeText(this.joinToken()).then(() => {
            this.tokenCopied.set(true);
            setTimeout(() => this.tokenCopied.set(false), 2000);
        });
    }

    openEdit(agent: Agent) {
        this.editingAgent.set({ ...agent });
        this.testResult.set(null);
        this.showDialog.set(true);
    }

    patchAgent(key: keyof Agent, value: unknown) {
        this.editingAgent.update(a => ({ ...a, [key]: value }));
    }

    testConnection() {
        this.testing.set(true);
        this.testResult.set(null);
        this.service.testAgent(this.editingAgent()).subscribe({
            next: (res) => {
                this.testing.set(false);
                this.testResult.set({ success: res.success, message: res.message || res.error || '' });
            },
            error: (err) => {
                this.testing.set(false);
                this.testResult.set({ success: false, message: err?.error?.error || this.translate.instant('admin.agents.connectionError') });
            },
        });
    }

    save() {
        this.saving.set(true);
        this.service.saveAgent(this.editingAgent()).subscribe({
            next: (res) => {
                this.saving.set(false);
                if (res.success) {
                    this.showDialog.set(false);
                    this.messageService.add({ severity: 'success', summary: this.translate.instant('common.saved'), detail: this.translate.instant('admin.agents.saved') });
                    this.load();
                } else {
                    this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: res.error || this.translate.instant('admin.agents.saveError') });
                }
            },
            error: (err) => {
                this.saving.set(false);
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: err?.error?.error || this.translate.instant('admin.agents.saveError') });
            },
        });
    }

    confirmDelete(agent: Agent) {
        this.confirmationService.confirm({
            message: this.translate.instant('admin.agents.confirmDelete', { name: agent.display_name }),
            header: this.translate.instant('admin.agents.confirmDeleteHeader'),
            icon: 'pi pi-exclamation-triangle',
            accept: () => this.delete(agent.id!),
        });
    }

    delete(id: string) {
        this.service.deleteAgent(id).subscribe({
            next: () => {
                this.messageService.add({ severity: 'success', summary: this.translate.instant('common.deleted'), detail: this.translate.instant('admin.agents.deleted') });
                this.load();
            },
            error: () => {
                this.messageService.add({ severity: 'error', summary: this.translate.instant('common.error'), detail: this.translate.instant('admin.agents.deleteError') });
            },
        });
    }
}
