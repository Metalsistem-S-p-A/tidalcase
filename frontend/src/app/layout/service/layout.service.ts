import { Injectable, computed, effect, signal } from '@angular/core';
import { Subject } from 'rxjs';

export interface layoutConfig {
    preset?: string;
    primary?: string;
    surface?: string | undefined | null;
    theme?: string;
    menuMode?: string;
}

interface LayoutState {
    staticMenuDesktopInactive?: boolean;
    overlayMenuActive?: boolean;
    configSidebarVisible?: boolean;
    staticMenuMobileActive?: boolean;
    menuHoverActive?: boolean;
}

interface MenuChangeEvent {
    key: string;
    routeEvent?: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class LayoutService {
    _config: layoutConfig = {
        preset: 'Aura',
        primary: 'blue',
        surface: null,
        theme: 'system',
        menuMode: 'static'
    };

    _state: LayoutState = {
        staticMenuDesktopInactive: false,
        overlayMenuActive: false,
        configSidebarVisible: false,
        staticMenuMobileActive: false,
        menuHoverActive: false
    };

    layoutConfig = signal<layoutConfig>(this.loadConfig());
    layoutState = signal<LayoutState>(this._state);

    private configUpdate = new Subject<layoutConfig>();
    private overlayOpen = new Subject<any>();
    private menuSource = new Subject<MenuChangeEvent>();
    private resetSource = new Subject();

    menuSource$ = this.menuSource.asObservable();
    resetSource$ = this.resetSource.asObservable();
    configUpdate$ = this.configUpdate.asObservable();
    overlayOpen$ = this.overlayOpen.asObservable();

    isSidebarActive = computed(() => this.layoutState().overlayMenuActive || this.layoutState().staticMenuMobileActive);
    getPrimary = computed(() => this.layoutConfig().primary);
    getSurface = computed(() => this.layoutConfig().surface);
    isOverlay = computed(() => this.layoutConfig().menuMode === 'overlay');
    transitionComplete = signal<boolean>(false);

    private initialized = false;
    private systemThemeListener?: (e: MediaQueryListEvent) => void;

    constructor() {
        this.toggleDarkMode(this.layoutConfig());
        this.attachSystemListener(this.layoutConfig().theme ?? 'system');

        effect(() => {
            const config = this.layoutConfig();
            if (config) {
                this.onConfigUpdate();
                this.saveConfig(config);
            }
        });

        effect(() => {
            const config = this.layoutConfig();
            if (!this.initialized || !config) {
                this.initialized = true;
                return;
            }
            this.handleDarkModeTransition(config);
            this.attachSystemListener(config.theme ?? 'system');
        });
    }

    isFollowingSystemTheme(): boolean {
        return (this.layoutConfig().theme ?? 'system') === 'system';
    }

    toggleDarkMode(config?: layoutConfig): void {
        const theme = (config ?? this.layoutConfig()).theme ?? 'system';
        if (this.resolveDark(theme)) {
            document.documentElement.classList.add('app-dark');
        } else {
            document.documentElement.classList.remove('app-dark');
        }
    }

    resetColorScheme(): void {
        this.layoutConfig.update((state) => ({
            ...state,
            preset: 'Aura',
            primary: 'blue',
            surface: null
        }));
    }

    resetAll(): void {
        localStorage.removeItem('layoutConfig');
        this.layoutConfig.set({ ...this._config });
        this.resetColorScheme();
    }

    onMenuToggle() {
        if (this.isOverlay()) {
            this.layoutState.update((prev) => ({ ...prev, overlayMenuActive: !this.layoutState().overlayMenuActive }));
            if (this.layoutState().overlayMenuActive) {
                this.overlayOpen.next(null);
            }
        }
        if (this.isDesktop()) {
            this.layoutState.update((prev) => ({ ...prev, staticMenuDesktopInactive: !this.layoutState().staticMenuDesktopInactive }));
        } else {
            this.layoutState.update((prev) => ({ ...prev, staticMenuMobileActive: !this.layoutState().staticMenuMobileActive }));
            if (this.layoutState().staticMenuMobileActive) {
                this.overlayOpen.next(null);
            }
        }
    }

    isDesktop() {
        return window.innerWidth > 991;
    }

    isMobile() {
        return !this.isDesktop();
    }

    onConfigUpdate() {
        this._config = { ...this.layoutConfig() };
        this.configUpdate.next(this.layoutConfig());
    }

    onMenuStateChange(event: MenuChangeEvent) {
        this.menuSource.next(event);
    }

    reset() {
        this.resetSource.next(true);
    }

    resolveDark(theme: string | undefined): boolean {
        if (theme === 'system') {
            return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
        }
        return theme === 'dark';
    }

    private attachSystemListener(theme: string): void {
        if (!window.matchMedia) return;
        const mq = window.matchMedia('(prefers-color-scheme: dark)');
        if (this.systemThemeListener) {
            mq.removeEventListener('change', this.systemThemeListener);
            this.systemThemeListener = undefined;
        }
        if (theme === 'system') {
            this.systemThemeListener = () => this.toggleDarkMode();
            mq.addEventListener('change', this.systemThemeListener);
        }
    }

    private loadConfig(): layoutConfig {
        try {
            const raw = localStorage.getItem('layoutConfig');
            if (raw) {
                return { ...this._config, ...JSON.parse(raw) };
            }
        } catch {}
        return { ...this._config };
    }

    private saveConfig(config: layoutConfig): void {
        try {
            const { theme, preset, primary, surface, menuMode } = config;
            localStorage.setItem('layoutConfig', JSON.stringify({ theme, preset, primary, surface, menuMode }));
        } catch {}
    }

    private handleDarkModeTransition(config: layoutConfig): void {
        if ((document as any).startViewTransition) {
            try {
                this.startViewTransition(config);
            } catch {
                this.toggleDarkMode(config);
                this.onTransitionEnd();
            }
        } else {
            this.toggleDarkMode(config);
            this.onTransitionEnd();
        }
    }

    private startViewTransition(config: layoutConfig): void {
        try {
            const transition = (document as any).startViewTransition(() => {
                this.toggleDarkMode(config);
            });
            if (transition?.ready?.then) {
                transition.ready.then(() => this.onTransitionEnd()).catch(() => this.onTransitionEnd());
            } else {
                this.onTransitionEnd();
            }
        } catch {
            this.toggleDarkMode(config);
            this.onTransitionEnd();
        }
    }

    private onTransitionEnd() {
        this.transitionComplete.set(true);
        setTimeout(() => this.transitionComplete.set(false));
    }
}