import { beforeAll, vi } from 'vitest';
import '@/fpan/declarations.d.ts';


beforeAll(() => {
    vi.mock('arches', () => ({
        default: '',
    }));

    vi.mock('vue3-gettext', () => ({
        useGettext: () => ({
            $gettext: (text: string) => (text)
        })
    }));
});
