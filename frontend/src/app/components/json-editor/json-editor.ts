import {
    ChangeDetectionStrategy,
    Component,
    ElementRef,
    OnDestroy,
    afterNextRender,
    effect,
    inject,
    input,
    output,
} from '@angular/core';
import { basicSetup } from 'codemirror';
import { json, jsonParseLinter } from '@codemirror/lang-json';
import { EditorState } from '@codemirror/state';
import { linter, lintGutter } from '@codemirror/lint';
import { EditorView } from '@codemirror/view';

@Component({
    selector: 'app-json-editor',
    template: '',
    changeDetection: ChangeDetectionStrategy.OnPush,
    styles: [`
        :host { display: block; }
        :host ::ng-deep .cm-editor {
            border: 1px solid var(--p-surface-300);
            border-radius: 6px;
            font-size: 13px;
        }
        :host ::ng-deep .cm-editor.cm-focused {
            outline: 2px solid var(--p-primary-color);
            outline-offset: 0;
            border-color: transparent;
        }
        :host ::ng-deep .cm-scroller {
            font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
            min-height: 160px;
        }
        :host ::ng-deep .cm-gutters {
            border-radius: 6px 0 0 6px;
        }
    `]
})
export class JsonEditorComponent implements OnDestroy {
    value = input<string>('{}');
    valueChange = output<string>();

    private host = inject(ElementRef<HTMLElement>);
    private view: EditorView | null = null;

    constructor() {
        afterNextRender(() => {
            this.view = new EditorView({
                state: EditorState.create({
                    doc: this.value(),
                    extensions: [
                        basicSetup,
                        json(),
                        linter(jsonParseLinter()),
                        lintGutter(),
                        EditorView.updateListener.of(update => {
                            if (update.docChanged) {
                                this.valueChange.emit(this.view!.state.doc.toString());
                            }
                        }),
                    ],
                }),
                parent: this.host.nativeElement,
            });
        });

        effect(() => {
            const newVal = this.value();
            if (this.view && this.view.state.doc.toString() !== newVal) {
                this.view.dispatch({
                    changes: { from: 0, to: this.view.state.doc.length, insert: newVal },
                });
            }
        });
    }

    ngOnDestroy() {
        this.view?.destroy();
    }
}
