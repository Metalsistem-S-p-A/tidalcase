import { Routes } from '@angular/router';
import { Access } from './access';
import { Error } from './error';
import { ForgotPasswordComponent } from './forgot-password/forgot-password';
import { Login } from './login';
import { ResetPasswordComponent } from './reset-password/reset-password';

export default [
    { path: 'access', component: Access },
    { path: 'error', component: Error },
    { path: 'login', component: Login },
    { path: 'forgot-password', component: ForgotPasswordComponent },
    { path: 'reset-password/:token', component: ResetPasswordComponent }
] as Routes;
