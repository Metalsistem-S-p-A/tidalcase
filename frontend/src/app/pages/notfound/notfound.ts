import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslateDirective, TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { AppTopbar } from '../../layout/component/app.topbar';

@Component({
    selector: 'app-notfound',
    standalone: true,
    imports: [RouterModule, ButtonModule, TranslatePipe, TranslateDirective, AppTopbar],
    templateUrl: './notfound.html'
})
export class Notfound { }
