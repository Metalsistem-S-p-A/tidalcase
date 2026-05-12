import { CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';
import { UserService } from '../../../services/user.service';

@Component({
    selector: 'app-reset-password',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        RouterModule,
        TranslateModule,
        PasswordModule,
        ButtonModule,
        MessageModule
    ],
    templateUrl: './reset-password.html'
})
export class ResetPasswordComponent implements OnInit {
    private userService = inject(UserService);
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private translateService = inject(TranslateService);

    token: string = '';
    newPassword: string = '';
    confirmPassword: string = '';
    isLoading: boolean = false;
    message: string = '';
    messageType: 'success' | 'error' = 'success';

    ngOnInit() {
        this.token = this.route.snapshot.params['token'];
    }

    resetPassword(): void {
        if (!this.newPassword || !this.confirmPassword) {
            this.messageType = 'error';
            this.message = this.translateService.instant('auth.errors.allFieldsRequired');
            return;
        }

        if (this.newPassword !== this.confirmPassword) {
            this.messageType = 'error';
            this.message = this.translateService.instant('auth.errors.passwordsDoNotMatch');
            return;
        }

        if (this.newPassword.length < 6) {
            this.messageType = 'error';
            this.message = this.translateService.instant('auth.errors.passwordTooShort');
            return;
        }

        this.isLoading = true;
        this.message = '';

        this.userService.resetPassword(this.token, this.newPassword).subscribe({
            next: () => {
                this.messageType = 'success';
                this.message = this.translateService.instant('auth.passwordResetSuccessfully');
                this.isLoading = false;

                // Redirect to login after 2 seconds
                setTimeout(() => {
                    this.router.navigate(['/auth/login']);
                }, 2000);
            },
            error: (error: any) => {
                this.messageType = 'error';
                this.message = error.error?.message || this.translateService.instant('auth.errors.passwordResetFailed');
                this.isLoading = false;
            }
        });
    }
}
