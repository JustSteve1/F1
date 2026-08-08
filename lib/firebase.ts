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

function getFirebaseApp(): FirebaseApp {
  if (getApps().length > 0) return getApps()[0]!;
  if (!hasConfig) {
    throw new Error(
      "Firebase is not configured (missing NEXT_PUBLIC_FIREBASE_API_KEY)",
    );
  }
  return initializeApp(firebaseConfig);
}

// Initialize only when config is present so `next build` prerender can succeed
// even if env injection is delayed; runtime still requires real keys.
const app: FirebaseApp | null = hasConfig
  ? getApps().length === 0
    ? initializeApp(firebaseConfig)
    : getApps()[0]!
  : null;

const auth: Auth | null = app ? getAuth(app) : null;
const db: Firestore | null = app ? getFirestore(app) : null;
const analytics: Analytics | null =
  app && typeof window !== "undefined" ? getAnalytics(app) : null;

export { app, auth, db, analytics, getFirebaseApp };
