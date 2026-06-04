export interface SharedNativeEdge {
    calleeLoc: string; // π.χ. "path/to/file.js:49:21:49:40"
    callerLoc: string | null; // π.χ. "path/to/file.js:10:5:20:5" ή null 
    patternName: string; // π.χ. "native:sqlite3.Database.once"
}

// Ο global πίνακας στη μνήμη
export const globalNativeEdgesStore: Array<SharedNativeEdge> = [];