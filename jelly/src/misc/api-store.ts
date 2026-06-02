import { Node } from "@babel/types";
import { ModuleInfo } from "../analysis/infos";

// Η δομή που θα κρατάμε στη μνήμη
export interface NativeCallEntry {
    callNode: Node;
    moduleInfo: ModuleInfo;
    nativeName: string;
}

// Global πίνακας προσβάσιμος από παντού
export const globalNativeCallsStore: Array<NativeCallEntry> = [];