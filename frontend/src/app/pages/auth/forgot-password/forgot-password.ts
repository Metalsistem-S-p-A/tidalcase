import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { UserService } from '../../../services/user.service';

@Component({
    selector: 'app-forgot-password',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        RouterModule,
        TranslateModule,
        InputTextModule,
        ButtonModule,
        MessageModule
    ],
    templateUrl: './forgot-password.html'
})
export class ForgotPasswordComponent {
    private userService = inject(UserService);
    private router = inject(Router);
    private translateService = inject(TranslateService);

    username: string = '';
    isLoading: boolean = false;
    message: string = '';
    messageType: 'success' | 'error' = 'success';
    sent: boolean = false;

    requestReset(): void {
        if (!this.username) {
            this.messageType = 'error';
            this.message = this.translateService.instant('auth.errors.usernameRequired');
            return;
        }

        this.isLoading = true;
        this.message = '';

        this.userService.forgotPassword(this.username).subscribe({
            next: (response: any) => {
                this.messageType = 'success';
                this.message = this.translateService.instant('auth.resetEmailSent');
                this.isLoading = false;
                this.sent = true;
            },
            error: (error: any) => {
                this.messageType = 'error';
                this.message = error.error?.message || this.translateService.instant('auth.errors.passwordResetFailed');
                this.isLoading = false;
            }
        });
    }
}
