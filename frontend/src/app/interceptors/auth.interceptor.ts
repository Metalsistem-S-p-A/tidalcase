import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    if (!req.url.startsWith('/api')) {
        return next(req);
    }
    return next(req.clone({ withCredentials: true }));
};
