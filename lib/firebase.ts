import { initializeApp, getApps, type FirebaseApp } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";
import { getAnalytics, type Analytics } from "firebase/analytics";
import { getFirestore, type Firestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

const hasConfig = Boolean(firebaseConfig.apiKey);

function initFirebaseApp(): FirebaseApp | null {
  if (!hasConfig) return null;
  try {
    if (getApps().length > 0) return getApps()[0]!;
    return initializeApp(firebaseConfig);
  } catch (err) {
    // Invalid/missing keys must not fail `next build` prerender on Vercel.
    console.warn(
      "[firebase] init skipped:",
      err instanceof Error ? err.message : String(err),
    );
    return null;
  }
}

const app: FirebaseApp | null = initFirebaseApp();

function safeGetAuth(firebaseApp: FirebaseApp | null): Auth | null {
  if (!firebaseApp) return null;
  try {
    return getAuth(firebaseApp);
  } catch (err) {
    console.warn(
      "[firebase] auth init skipped:",
      err instanceof Error ? err.message : String(err),
    );
    return null;
  }
}

function safeGetFirestore(firebaseApp: FirebaseApp | null): Firestore | null {
  if (!firebaseApp) return null;
  try {
    return getFirestore(firebaseApp);
  } catch (err) {
    console.warn(
      "[firebase] firestore init skipped:",
      err instanceof Error ? err.message : String(err),
    );
    return null;
  }
}

// Cast keeps existing call sites typing clean; AuthContext/admin guard null at runtime.
const auth = safeGetAuth(app) as Auth;
const db = safeGetFirestore(app) as Firestore;
const analytics: Analytics | null =
  app && typeof window !== "undefined" ? getAnalytics(app) : null;

export { app, auth, db, analytics };
