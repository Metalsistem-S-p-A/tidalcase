import { ChangeDetectionStrategy, Component, ElementRef, NgZone, OnDestroy, OnInit, inject, signal, viewChild } from '@angular/core';
import { Location } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { DomSanitizer, SafeResourceUrl, Title } from '@angular/platform-browser';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../services/auth.service';
import { TideService, SessionFile, TideInstance } from '../../services/tide.service';
import mpegts from 'mpegts.js';

@Component({
    selector: 'app-session',
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [TranslateModule],
    templateUrl: './session.html'
})
export class SessionPage implements OnInit, OnDestroy {
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private sanitizer = inject(DomSanitizer);
    private authService = inject(AuthService);
    private tideService = inject(TideService);
    private translateService = inject(TranslateService);
    private zone = inject(NgZone);
    private location = inject(Location);
    private titleService = inject(Title);
    private defaultTitle = this.titleService.getTitle();

    private vncIframe = viewChild<ElementRef<HTMLIFrameElement>>('vncIframe');
    private audioRef = viewChild<ElementRef<HTMLAudioElement>>('audioElement');
    private instanceId = '';
    private agentBase = '';
    private clipboardInputTimer?: ReturnType<typeof setTimeout>;

    canAudio = signal(false);
    canUpload = signal(false);
    canDownload = signal(false);
    qualityLevel = signal<'0' | '1' | '2' | '3' | '4'>('2');
    readonly qualityOptions: { v: '0' | '1' | '2' | '3' | '4'; key: string }[] = [
        { v: '0', key: 'session.qualityStatic' },
        { v: '1', key: 'session.qualityLow' },
        { v: '2', key: 'session.qualityMedium' },
        { v: '3', key: 'session.qualityHigh' },
        { v: '4', key: 'session.qualityMax' },
    ];

    isGuacSession = signal(false);

    connected = signal(false);
    connectionFailed = signal(false);
    panelVisible = signal(false);
    isFullscreen = signal(false);
    clipboardOpen = signal(false);
    clipboardText = signal('');
    audioActive = signal(false);
    progress = signal('');
    instance = signal<TideInstance | null>(null);
    iframeUrl = signal<SafeResourceUrl | null>(null);
    player?: mpegts.Player;

    resizeMode = signal<'off' | 'scale' | 'remote'>('remote');
    readonly resizeOptions: { v: 'off' | 'scale' | 'remote'; key: string }[] = [
        { v: 'off', key: 'session.resizeOff' },
        { v: 'scale', key: 'session.resizeScale' },
        { v: 'remote', key: 'session.resizeRemote' },
    ];
    readonly resolutionPresets = [
        { w: 1280, h: 720, l: '720p' },
        { w: 1920, h: 1080, l: '1080p' },
        { w: 2560, h: 1440, l: '1440p' },
    ];
    gameModeActive = signal(false);
    keyboardVisible = signal(false);
    displaysOpen = signal(false);
    hidpiActive = signal(false);
    threadingActive = signal(false);
    webrtcActive = signal(false);
    perfStatsActive = signal(false);
    kasmAudioAvailable = signal(false);
    canControlDisplays = signal(false);
    qualityOpen = signal(false);
    tabVisible = signal(true);
    private tabHideTimer?: ReturnType<typeof setTimeout>;

    onTabEnter() {
        clearTimeout(this.tabHideTimer);
        if (!this.tabVisible()) this.tabVisible.set(true);
    }

    onTabLeave() {
        if (!this.panelVisible()) {
            clearTimeout(this.tabHideTimer);
            this.tabHideTimer = setTimeout(() => this.tabVisible.set(false), 2000);
        }
    }

    resizeOpen = signal(false);
    controlsOpen = signal(false);
    advancedOpen = signal(false);

    downloadsOpen = signal(false);
    downloads = signal<SessionFile[]>([]);
    downloadsLoading = signal(false);
    uploading = signal(false);
    uploadSuccess = signal(false);
    private fileInput?: HTMLInputElement;

    private mode = this.route.snapshot.queryParamMap.get("mode");

    private onMessage = (e: MessageEvent) => {
        if (e.data?.action == 'connection_state') {
            if (e.data?.value == 'connected') {
                this.progress.set(this.translateService.instant("session.connected"));
                this.connected.set(true);
                this._postToVnc({ action: 'control_displays' });
                const idleMinutes = this.instance()?.tide?.session_idle_time_limit;
                // Force KasmVNC state to match our initial signals (KasmVNC persists state in localStorage)
                this._postToVnc({ action: 'resize', value: 'off' });
                // set_idle_timeout must come after the resize postMessage because the resize
                // handler in KasmVNC overwrites rfb.idleDisconnect from the stored setting.
                setTimeout(() => {
                    this._postToVnc({ action: 'resize', value: this.resizeMode() });
                    if (idleMinutes) this._postToVnc({ action: 'set_idle_timeout', value: idleMinutes * 60 });
                }, 1000);
                this._postToVnc({ action: 'disable_game_mode' });
                this._postToVnc({ action: 'hide_keyboard_controls' });
                this._postToVnc({ action: 'close_displays_mode' });
                this._postToVnc({ action: 'enable_hidpi', value: false });
                this._postToVnc({ action: 'enable_threading', value: false });
                this._postToVnc({ action: 'disable_webrtc' });
                this._postToVnc({ action: 'set_perf_stats', value: false });
            }
            else if (e.data?.value == 'init') {
                this.progress.set(this.translateService.instant("session.init"));
                this.connected.set(false);
            }
            else if (e.data?.value == 'connecting' || e.data?.value == 'reconnecting') {
                this.progress.set(this.translateService.instant("session.loading"));
                this.connected.set(false);
            }
            else if (e.data?.value == 'disconnected' || e.data?.value == 'failed') {
                const errorMsg: string | undefined = e.data?.error;
                if (errorMsg && this.isGuacSession()) {
                    this.zone.run(() => {
                        this.connectionFailed.set(true);
                        this.progress.set(errorMsg);
                        setTimeout(() => this.terminate(), 3000);
                    });
                } else if (!this.connectionFailed()){
                    this.disconnect();
                }
            }
        } else if (e.data?.action == 'togglenav') {
            this.togglePanel();
        }
        else if (e.data?.action == 'clipboardrx') {
            const text = e.data?.value;
            if (typeof text === 'string') {
                this.zone.run(() => {
                    this.clipboardText.set(text);
                    navigator.clipboard.writeText(text).catch(() => {});
                });
            }
        }
        else if (e.data?.action == 'enable_audio') {
            this.kasmAudioAvailable.set(true);
        }
        else if (e.data?.action == 'can_control_displays') {
            if (e.data?.value === true) this.canControlDisplays.set(true);
        }
        else if (e.data?.action == 'idle_session_timeout') {
            this.progress.set(this.translateService.instant('session.idleTimeout'));
            this.connected.set(false);
            this.terminate();
        }
    };

    ngOnInit() {
        
        this.instanceId = this.route.snapshot.paramMap.get('instanceId') ?? '';
        if (!this.instanceId) {
            this.router.navigate(['/']);
            return;
        }

        const token = this.route.snapshot.queryParamMap.get('t');
        if (token) {
            this.authService.storeToken(token);
            this.location.replaceState('/session/' + this.instanceId);
        }

        const u = this.authService.currentUser();
        if(u) {
            this.canAudio.set(u.settings["allow_audio"]);
            this.canUpload.set(u.settings["allow_uploads"]);
            this.canDownload.set(u.settings["allow_downloads"]);
        }
        
        //this.videoQualityElement = (this.vncIframe()?.nativeElement.contentDocument?.getElementById('noVNC_setting_video_quality') as HTMLInputElement);
        //this.qualityLevel.set(this.videoQualityElement.value);

        window.addEventListener('message', this.onMessage);
        document.addEventListener('fullscreenchange', this.onFullscreenChange);
        this.tabHideTimer = setTimeout(() => this.tabVisible.set(false), 3000);

        this.tideService.getMyInstances().subscribe({
            next: (res) => {
                if(!res) return;
                const i = res.instances.find(i => i.id === this.instanceId);
                this.instance.set(i ?? null);
                if (!this.instance()) {
                    this.disconnect();
                    return;
                }
                const tideName = this.instance()?.tide?.display_name;
                if (tideName) this.titleService.setTitle("Tidalcase - " + tideName);

                const tideType = this.instance()?.tide?.tide_type;
                const isGuac = tideType === 'vnc' || tideType === 'rdp' || tideType === 'ssh';
                this.isGuacSession.set(isGuac);
                if (isGuac) {
                    this.progress.set(this.translateService.instant('session.loading'));
                    this.tideService.getTideInfo(this.instanceId).subscribe({
                        next: (info) => {
                            const base = info.vnc_url ?? this.instance()?.vnc_url;
                            if (base && info.guac_token) {
                                const url = `${base}vnc.html?instance_id=${this.instanceId}&guac_token=${encodeURIComponent(info.guac_token)}`;
                                this.iframeUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(url));
                                this.progress.set(this.translateService.instant('session.connected'));
                                this.connected.set(true);
                            }
                        },
                        error: () => this.disconnect(),
                    });
                } else if (this.instance()?.vnc_url) {
                    const parsed = new URL(this.instance()?.vnc_url!);
                    this.agentBase = `${parsed.protocol}//${parsed.host}`;
                    this.iframeUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(this.instance()?.vnc_url!));
                }
            },
            error: () => {
                this.disconnect();
            }
        });
    }

    ngOnDestroy() {
        window.removeEventListener('message', this.onMessage);
        clearTimeout(this.clipboardInputTimer);
        clearTimeout(this.tabHideTimer);
        document.removeEventListener('fullscreenchange', this.onFullscreenChange);
        this.stopAudio();
        this.titleService.setTitle(this.defaultTitle);
    }

    togglePanel() {
        this.panelVisible.update(v => !v);
        if (!this.panelVisible()) {
            this.clipboardOpen.set(false);
            this.tabVisible.set(true);
            clearTimeout(this.tabHideTimer);
            this.tabHideTimer = setTimeout(() => this.tabVisible.set(false), 2000);
        }
    }

    toggleClipboard() {
        this.clipboardOpen.update(v => !v);
        if (this.clipboardOpen()) {
            navigator.clipboard.readText().then(t => this.clipboardText.set(t)).catch(() => {});
        }
    }

    onClipboardFocus() {
        navigator.clipboard.readText().then(t => this.clipboardText.set(t)).catch(() => {});
    }

    onClipboardInput(e: Event) {
        const text = (e.target as HTMLTextAreaElement).value;
        this.clipboardText.set(text);
        navigator.clipboard.writeText(text).catch(() => {});

        clearTimeout(this.clipboardInputTimer);
        this.clipboardInputTimer = setTimeout(() => this.postClipboardToIframe(text), 300);
    }

    private postClipboardToIframe(text: string) {
        this._postToVnc({ action: 'clipboardsnd', value: text });
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
        this.togglePanel();
    }

    toggleDownloads() {
        this.downloadsOpen.update(v => !v);
        if (this.downloadsOpen()) this.loadDownloads();
    }

    loadDownloads() {
        this.downloadsLoading.set(true);
        this.tideService.listDownloads(this.instanceId).subscribe({
            next: (res) => {
                this.downloads.set(res.files || []);
                this.downloadsLoading.set(false);
            },
            error: () => { this.downloadsLoading.set(false); }
        });
    }

    downloadFile(filename: string) {
        this.tideService.downloadFile(this.instanceId, filename).subscribe({
            next: (blob) => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            },
        });
    }

    formatFileSize(bytes: number): string {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    openUpload() {
        if (!this.fileInput) {
            this.fileInput = document.createElement('input');
            this.fileInput.type = 'file';
            this.fileInput.multiple = true;
            this.fileInput.onchange = (e) => this.onFileSelected(e);
        }
        this.fileInput.value = '';
        this.fileInput.click();
    }

    onFileSelected(event: Event) {
        const files = (event.target as HTMLInputElement).files;
        if (!files) return;
        this.uploading.set(true);
        this.uploadSuccess.set(false);
        this.tideService.uploadFile(this.instanceId, files).subscribe({
            next: () => {
                this.uploading.set(false);
                this.uploadSuccess.set(true);
                setTimeout(() => this.zone.run(() => this.uploadSuccess.set(false)), 3000);
            },
            error: () => { this.uploading.set(false); }
        });
    }

    private _postToVnc(data: object) {
        this.vncIframe()?.nativeElement.contentWindow?.postMessage(data, '*');
    }

    setResize(mode: 'off' | 'scale' | 'remote') {
        this.resizeMode.set(mode);
        this._postToVnc({ action: 'resize', value: mode });
        const idleMinutes = this.instance()?.tide?.session_idle_time_limit;
        if (idleMinutes) this._postToVnc({ action: 'set_idle_timeout', value: idleMinutes * 60 });
    }

    setResolution(w: number, h: number) {
        this._postToVnc({ action: 'set_resolution', value_x: w, value_y: h });
        const idleMinutes = this.instance()?.tide?.session_idle_time_limit;
        if (idleMinutes) this._postToVnc({ action: 'set_idle_timeout', value: idleMinutes * 60 });
    }

    toggleGameMode() {
        const next = !this.gameModeActive();
        this.gameModeActive.set(next);
        this._postToVnc({ action: next ? 'enable_game_mode' : 'disable_game_mode' });
    }

    toggleKeyboard() {
        const next = !this.keyboardVisible();
        this.keyboardVisible.set(next);
        this._postToVnc({ action: next ? 'show_keyboard_controls' : 'hide_keyboard_controls' });
    }

    toggleDisplays() {
        const next = !this.displaysOpen();
        this.displaysOpen.set(next);
        this._postToVnc({ action: next ? 'open_displays_mode' : 'close_displays_mode' });
    }

    toggleHidpi() {
        const next = !this.hidpiActive();
        this.hidpiActive.set(next);
        this._postToVnc({ action: 'enable_hidpi', value: next });
    }

    toggleThreading() {
        const next = !this.threadingActive();
        this.threadingActive.set(next);
        this._postToVnc({ action: 'enable_threading', value: next });
    }

    toggleWebrtc() {
        const next = !this.webrtcActive();
        this.webrtcActive.set(next);
        this._postToVnc({ action: next ? 'enable_webrtc' : 'disable_webrtc' });
    }

    togglePerfStats() {
        const next = !this.perfStatsActive();
        this.perfStatsActive.set(next);
        this._postToVnc({ action: 'set_perf_stats', value: next });
    }

    disconnect() {
        if (this.mode != 'current') {
            window.close();
            setTimeout(() => this.router.navigate(['/']), 300);
        } else {
            this.router.navigate(['/']);
        }
    }

    terminate() {
        this.tideService.destroyInstance(this.instanceId).subscribe({
            complete: () => this.disconnect(),
            error: () => this.disconnect(),
        });
    }

    setQuality(level: '0' | '1' | '2' | '3' | '4') {
        this.qualityLevel.set(level);
        this._postToVnc({ action: 'setvideoquality', qualityLevel: parseInt(level) });
    }

    getTypeIcon(type: string): string {
        const map: Record<string, string> = { container: 'pi pi-desktop', vnc: 'pi pi-window-maximize', rdp: 'pi pi-microsoft', ssh: 'pi pi-code' };
        return map[type] ?? 'pi pi-desktop';
    }

    onFullscreenChange = () => {
        this.isFullscreen.set(!!document.fullscreenElement);
    };

    toggleAudio() {
        if (this.audioActive()) {
            this.stopAudio();
        } else {
            this.startAudioStream();
        }
    }

    private startAudioStream(): void {
        if (!mpegts.getFeatureList().mseLivePlayback) return;
        const audioEl = this.audioRef()?.nativeElement;
        if (!audioEl) return;
        const wsBase = this.agentBase.replace(/^http/, 'ws');
        this.player = mpegts.createPlayer({
            type: 'mpegts',
            isLive: true,
            url: `${wsBase}/desktop/${this.instanceId}/audio/`,
            hasVideo: false,
            hasAudio: true,
        }, {
            enableStashBuffer: false,
            liveBufferLatencyChasing: true,
            liveBufferLatencyMaxLatency: 0.5,
            liveBufferLatencyMinRemain: 0.1,
            liveSync: true,
        });
        this.player.attachMediaElement(audioEl);
        this.player.load();
        this.player.play();
        this.audioActive.set(true);
    }

    private stopAudio(): void {
        if (this.player) {
            this.player.pause();
            this.player.unload();
            this.player.detachMediaElement();
            this.player.destroy();
            this.player = undefined;
        }
        this.audioActive.set(false);
    }
}
