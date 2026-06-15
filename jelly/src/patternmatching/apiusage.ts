import logger from "../misc/logger";
import {mapGetSet, locationToStringWithFileAndEnd, Location, SimpleLocation} from "../misc/util";
import {
    //AbbreviatedPathPattern,
    AccessPathPattern,
    CallResultAccessPathPattern,
    ComponentAccessPathPattern,
    ImportAccessPathPattern,
    PropertyAccessPathPattern
} from "./patterns";
import {isCallExpression, isNewExpression, isOptionalCallExpression, Node} from "@babel/types";
import {AccessPathPatternCanonicalizer} from "./patternparser";
import {AccessPath} from "../analysis/accesspaths";
import {FragmentState} from "../analysis/fragmentstate";


//import { globalNativeEdgesStore } from "./nativestore";


export type PatternType = "import" | "read" | "write" | "call" | "component";

export type AccessPathPatternToNodes = Record<PatternType, Map<AccessPathPattern, Set<Node>>>;
export type NodeToAccessPathPatterns = Record<PatternType, Map<Node, Set<AccessPathPattern>>>;
export type AccessPathString = string;
export type AccessPathPatternToLocations = Record<PatternType, Record<AccessPathString, Array<SimpleLocation & {filename: string}>>>;


//DEBUG
import {FunctionInfo, ModuleInfo} from "../analysis/infos";
//import { GlobalState } from "../analysis/globalstate";
// Map που συνδέει το ID του Node με μια λίστα από callers
//const nodeToCallers = new Map<number, Array<{name: string, loc: string}>>();


/**
 * Finds the usage of the API of external modules.
 */
export function getAPIUsage(f: FragmentState): [AccessPathPatternToNodes, NodeToAccessPathPatterns] {
    logger.info("Collecting API usage");
    const reached: AccessPathPatternToNodes = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const res1: AccessPathPatternToNodes = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const res2: NodeToAccessPathPatterns = {import: new Map, read: new Map, write: new Map, call: new Map, component: new Map};
    const c = new AccessPathPatternCanonicalizer;
    const worklist = new Map<AccessPathPattern, Set<AccessPath>>();

    function add(t: PatternType, p: AccessPathPattern, ap: AccessPath, n: Node) {
        // Καθαρισμός του pattern μέσω του canonicalizer (χωρίς abbreviations)
        p = c.canonicalize(p);
        
        const aps = mapGetSet(reached[t], p);
        if (!aps.has(n)) {
            if (logger.isDebugEnabled())
                logger.debug(`Found ${t} ${p} at ${locationToStringWithFileAndEnd(n.loc)}`);
            aps.add(n);

            function isReadAtCall(): boolean {
                if (t === "read") {
                    const m = f.callResultAccessPaths.get(ap);
                    if (m)
                        for (const f of m.keys())
                            if ((isCallExpression(f) || isOptionalCallExpression(f) || isNewExpression(f)) && f.callee === n)
                                return true;
                }
                return false;
            }

            if (isReadAtCall()) { 
                if (logger.isDebugEnabled())
                    logger.debug(`Read-call ${ap} at ${locationToStringWithFileAndEnd(n.loc)}`);
            } else {
                mapGetSet(res1[t], p).add(n);
                mapGetSet(res2[t], n).add(p);
            }
            mapGetSet(worklist, p).add(ap);
        }
    } // κλείνει σωστά η add

    // find imports
    for (const [ap, m] of f.moduleAccessPaths)
        for (const n of m.keys())
            add("import", c.canonicalize(new ImportAccessPathPattern(ap.moduleInfo.getOfficialName())), ap, n);

    // iteratively find property reads, writes, calls and components
    for (const [p, aps] of worklist)
        for (const ap of aps) {
            aps.delete(ap);
            if (aps.size === 0)
                worklist.delete(p);
            
            // property reads
            const m1 = f.propertyReadAccessPaths.get(ap);
            if (m1)
                for (const [prop, np] of m1)
                    for (const [n2, {bp}] of np)
                        add("read", c.canonicalize(new PropertyAccessPathPattern(p, [prop])), bp, n2);
            
            // property writes
            const m2 = f.propertyWriteAccessPaths.get(ap);
            if (m2)
                for (const [prop, np] of m2)
                    for (const [n2, {bp}] of np)
                        add("write", c.canonicalize(new PropertyAccessPathPattern(p, [prop])), bp, n2);

            // calls
            const m3 = f.callResultAccessPaths.get(ap);
            if (m3)
                for (const [n2, {bp}] of m3)
                    add("call", c.canonicalize(new CallResultAccessPathPattern(p)), bp, n2);

            // components
            const m4 = f.componentAccessPaths.get(ap);
            if (m4)
                for (const [n2, {bp}] of m4)
                    add("component", c.canonicalize(new ComponentAccessPathPattern(p)), bp, n2);
        }

    return [res1, res2];
}

export function reportAPIUsage(r1: AccessPathPatternToNodes, r2: NodeToAccessPathPatterns) { // TODO: split into two functions?
    logger.info("API usage, access path patterns -> nodes:");
    let numAccessPathPatterns = 0, numAccessPathPatternsAtNodes = 0;
    for (const [t, m] of Object.entries(r1)) {
        for (const [p, ns] of m) {
            logger.info(`${t} ${p}:`);
            for (const n of ns)
                logger.info(`  ${locationToStringWithFileAndEnd(n.loc)}`);
            numAccessPathPatternsAtNodes += ns.size;
        }
        numAccessPathPatterns += m.size;
    }
    logger.info(`Access path patterns: ${numAccessPathPatterns}, access path patterns at nodes: ${numAccessPathPatternsAtNodes}`);
}

//DEBUG
//export function convertAPIUsageToJSON(r: AccessPathPatternToNodes): AccessPathPatternToLocations {
  //  const res: AccessPathPatternToLocations = {import: {}, read: {}, write: {}, call: {}, component: {}};
    //for (const type of Object.getOwnPropertyNames(r) as Array<PatternType>) {
      //  const t: Record<AccessPathString, Array<SimpleLocation & {filename: string}>> = {};
        //for (const [p, nodes] of r[type]) {
          //  const a: Array<SimpleLocation & {filename: string}> = [];
            //for (const n of nodes)
              //  if (n.loc) {
                //    const loc = n.loc as Location;
                  //  if (loc.module)
                    //    a.push({filename: loc.module.getPath(), start: loc.start, end: loc.end});
                //}
//            t[p.toString()] = a;
  //      }
    //    res[type] = t;
//    }
  //  return res;
//}

//import {AnalysisStateReporter} from "../output/analysisstatereporter";

//DEBUG
// Βοηθητική συνάρτηση για να καθαρίζει τους callers βάσει ΜΟΝΟ του Loc
function deduplicateCallers(callers: any[]): any[] {
    const seenLocs = new Set();
    return callers.filter(c => {
        const key = c.loc; 
        if (seenLocs.has(key)) return false;
        seenLocs.add(key);
        return true;
    });
}

// DEBUG
// Ορισμός ενός σταθερού counter εκτός της συνάρτησης για τις Artificial C συναρτήσεις
let cFunctionIdCounter = 9000; 

export function convertAPIUsageToJSON(r: AccessPathPatternToNodes, _?: any, f?: any): any {
    const res: any = {import: {}, read: {}, write: {}, call: {}, component: {}};
    
    let gasketBridges: any[] = [];
    try {
        const fs = require("fs");
        const jsonPath = "/home/eva/Ptuxiakh/jelly/src/analysis/bridges_sqlite3.json";
        console.log(` [GASKET CHECK] Looking for JSON at: ${jsonPath} -> Found? ${fs.existsSync(jsonPath)}`);
        if (fs.existsSync(jsonPath)) {
            const raw = fs.readFileSync(jsonPath, "utf-8");
            const parsed = JSON.parse(raw);
            gasketBridges = parsed.bridges || []; 
            logger.info(`[GASKET] Loaded ${gasketBridges.length} bridges for matching inside API usage stage.`);
        }
    } catch (e: any) {
        logger.warn(`[GASKET] Could not load bridges_sqlite3.json: ${e.message}`);
    }

    const seenGlobalNodes = new Set<string>();

    for (const type of Object.getOwnPropertyNames(r) as Array<PatternType>) {
        const t: Record<string, any> = {};
        for (const [p, nodes] of r[type]) {
            const a: Array<any> = [];

            for (const n of nodes) {
                if (n.loc) {
                    const loc = n.loc as Location;
                    const locKey = locationToStringWithFileAndEnd(n.loc);
                    const filename = loc.module?.getPath() || "";
                    
                    const dedupeKey = `${filename}:${loc.start.line}:${loc.start.column}:${type}`;
                    const patternName = `native:${p.toString()}`;

                    const callersList = f ? (f.nodeToCallers.get(locKey as any) || []) : [];
                    const deduplicatedCallers = deduplicateCallers(callersList);

                    const calleeName = `${loc.start.line}:${loc.start.column}:${loc.end.line}:${loc.end.column}`;
                    const calleeLoc = `${filename}:${calleeName}`;

                    // 1. Καταγραφή στο JSON output chunk
                    if (deduplicatedCallers.length === 0) {
                        a.push({ callee: { name: calleeName, loc: calleeLoc }, caller: null });
                    } else {
                        for (const c of deduplicatedCallers) {
                            a.push({
                                callee: { name: calleeName, loc: calleeLoc },
                                caller: { name: c.name, loc: c.loc }
                            });
                        }
                    }

                    // 2. Ενημέρωση του Call Graph και Matching
                    if (!seenGlobalNodes.has(dedupeKey)) {
                        seenGlobalNodes.add(dedupeKey);

                        const targetModule = loc.module;
                        if (targetModule) {
                            const nativeCalleeInfo = f.a.registerNativeFunctionInfo(targetModule, n, patternName);
                            
                            if (deduplicatedCallers.length === 0) {
                                f.registerRealNativeCallEdge(n, targetModule, nativeCalleeInfo);
                            } else {
                                for (let i = 0; i < deduplicatedCallers.length; i++) {
                                    let jsCallerInfo: FunctionInfo | ModuleInfo = targetModule;
                                    for (const fun of f.a.functionInfos.values()) {
                                        if (fun.loc && fun.moduleInfo === targetModule && !fun.isNative) {
                                            if (n.loc.start.line >= fun.loc.start.line && n.loc.end.line <= fun.loc.end.line) {
                                                jsCallerInfo = fun;
                                                break;
                                            }
                                        }
                                    }
                                    f.registerRealNativeCallEdge(n, jsCallerInfo, nativeCalleeInfo);
                                }
                            }

                            // C-BRIDGE MATCHING ΛΟΓΙΚΗ
                            const matchedCfunc = findGasketCfuncMatch(patternName, gasketBridges);
                            if (matchedCfunc) {
                                (nativeCalleeInfo as any).cfunc = matchedCfunc;
                                (nativeCalleeInfo as any).hasCBridge = true;

                                const cFuncName = `[C Function] ${matchedCfunc}`;
                                
                                // Αναζήτηση αν υπάρχει ήδη η C συνάρτηση καταγεγραμμένη καθολικά
                                const artificialStrKey = `CFunctionNode:${matchedCfunc}`;
                                let cFuncInfo = f.a.functionInfos.get(artificialStrKey);

                                if (!cFuncInfo) {
                                    cFuncInfo = new FunctionInfo(cFuncName, n.loc!, targetModule, false, true);
                                    
                                    // Ανάθεση σταθερού, μοναδικού ID που δεν επηρεάζεται από το μέγεθος των maps
                                    (cFuncInfo as any).id = String(cFunctionIdCounter++);
                                    
                                    targetModule.functions.add(cFuncInfo);
                                    f.a.functionInfos.set(artificialStrKey, cFuncInfo);
                                    
                                    if (f.functions) f.functions.add(cFuncInfo);
                                }

                                // Διασφάλιση σύνδεσης της Native JS με τη C Function
                                f.registerRealNativeCallEdge(n, nativeCalleeInfo, cFuncInfo);

                                // Εξαναγκασμός του exporter να συμπεριλάβει την ακμή
                                const callEdges = mapGetSet(f.callToFunction, n);
                                callEdges.add(cFuncInfo);
                            }
                        }
                    }
                }
            }
            t[p.toString()] = a;
        }
        res[type] = t;
    }
    return res;
}

function levenshteinDistance(s1: string, s2: string): number {
    const m = s1.length, n = s2.length;
    const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (s1[i - 1] === s2[j - 1]) dp[i][j] = dp[i - 1][j - 1];
            else dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + 1);
        }
    }
    return dp[m][n];
}

function extractStructuralTokens(fqnString: string): string[] {
    let s = fqnString.replace(/^<[^>]+>(\(\))?/, "");

    if (s.includes("/")) {
        const parts = s.split("/");
        s = parts[parts.length - 1];
    }

    s = s.replace(/\(\)/g, "")
         .replace(/\.prototype/g, "")
         .replace(/\.GET/g, "") 
         .replace(/\.SET/g, "")
    //     .replace(/finalize_/g, "finalize"); // Ευθυγράμμιση C / JS ονόματος

    let tokens = s.split(".").map(t => t.trim().toLowerCase()).filter(t => t.length > 0);

    const garbageTokens = new Set(["apply", "constructor", "binding", "node_sqlite3"]);
    tokens = tokens.filter(t => !garbageTokens.has(t));

    return tokens;
}

function findGasketCfuncMatch(jellyPattern: string, gasketBridges: any[]): string | undefined {
    // Αφαιρώ "native:" αν υπάρχει
    const cleanJellyPattern = jellyPattern.replace(/^native:/, "");
    
    const jTokens = extractStructuralTokens(cleanJellyPattern);
    if (jTokens.length === 0) return undefined;

    let bestMatch: any = null;
    let highestSimilarity = 0;
    const threshold = 0.7;

    for (const bridge of gasketBridges) {
        if (!bridge.jsname) continue;
        
        const gTokens = extractStructuralTokens(bridge.jsname);

        if (jTokens.length !== gTokens.length) {
            continue;
        }

        // Ένωση των tokens για τον έλεγχο Levenshtein
        const jCleanStr = jTokens.join("");
        const gCleanStr = gTokens.join("");

        // Υπολογισμός Levenshtein 
        const maxLen = Math.max(jCleanStr.length, gCleanStr.length);
        if (maxLen === 0) continue;
        const distance = levenshteinDistance(jCleanStr, gCleanStr);
        const similarity = 1 - distance / maxLen;

        // EXACT MATCH 
        if (similarity === 1.0) {
            highestSimilarity = 1.0;
            bestMatch = bridge;
            break; 
        }

        if (similarity > threshold && similarity > highestSimilarity) {
            highestSimilarity = similarity;
            bestMatch = bridge;
        }
    }

    //debug μήνυμα
    if (bestMatch) {
        console.log(` [MATCH DETECTED]`);
        console.log(JSON.stringify({
            "jelly_pattern": jellyPattern,
            "gasket_jsname": bestMatch["jsname"],
            "cfunc": bestMatch["cfunc"],
            "confidence": Number(highestSimilarity.toFixed(2))
        }, null, 2));
        console.log("--------------------------------------------------");

        return bestMatch.cfunc; 
    }

    return undefined;
}