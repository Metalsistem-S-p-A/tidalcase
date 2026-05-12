import { Injectable } from '@angular/core';
import { MissingTranslationHandler, MissingTranslationHandlerParams } from '@ngx-translate/core';

@Injectable()
export class MissingTranslationExceptionHandler implements MissingTranslationHandler {
    handle(params: MissingTranslationHandlerParams): string {
        // Return a formatted message instead of just the key
        return `[MISSING: ${params.key}]`;
    }
}