import { Component } from '@angular/core';
import { TranslatePipe } from "@ngx-translate/core";
@Component({
    standalone: true,
    imports: [TranslatePipe],
    selector: 'app-footer',
    templateUrl: './app.footer.html'
})
export class AppFooter {
    githubUrl = 'https://github.com/mlongo4290/acme-certificates-manager';
}
