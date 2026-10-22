import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  where,
  orderBy,
  setDoc,
  addDoc,
  updateDoc,
  serverTimestamp,
  onSnapshot,
} from 'firebase/firestore';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { db, storage, auth } from './firebaseConfig';

/**
 * Direct Client-Side Firestore Service for Arshith Connect
 * Connects directly to the existing collections:
 * - admins
 * - attendance
 * - employees
 * - notifications
 * - officeSettings
 * - settings
 */

// 1. Employees Collection
export const getEmployeesFromFirestore = async () => {
  const colRef = collection(db, 'employees');
  const snapshot = await getDocs(colRef);
  return snapshot.docs.map((doc) => ({
    id: doc.id,
    ...doc.data(),
  }));
};

export const getEmployeeByUid = async (uid) => {
  const docRef = doc(db, 'employees', uid);
  const snap = await getDoc(docRef);
  if (snap.exists()) {
    return { id: snap.id, ...snap.data() };
  }
  return null;
};

// 2. Attendance Collection
export const getAttendanceRecordsFromFirestore = async (employeeId = null) => {
  const colRef = collection(db, 'attendance');
  let q = colRef;
  if (employeeId) {
    q = query(colRef, where('employee_id', '==', employeeId));
  }
  const snapshot = await getDocs(q);
  return snapshot.docs.map((doc) => ({
    id: doc.id,
    ...doc.data(),
  }));
};

// 3. Notifications Collection
export const getNotificationsFromFirestore = async () => {
  const colRef = collection(db, 'notifications');
  const snapshot = await getDocs(colRef);
  return snapshot.docs.map((doc) => ({
    id: doc.id,
    ...doc.data(),
  }));
};

// 4. Office Settings Collection
export const getOfficeSettingsFromFirestore = async () => {
  const docRef = doc(db, 'officeSettings', 'timings');
  const snap = await getDoc(docRef);
  if (snap.exists()) {
    return snap.data();
  }
  // Fallback to checking all documents in collection
  const colRef = collection(db, 'officeSettings');
  const snapshot = await getDocs(colRef);
  if (!snapshot.empty) {
    return snapshot.docs[0].data();
  }
  return null;
};

// 5. System Settings Collection
export const getSettingsFromFirestore = async () => {
  const colRef = collection(db, 'settings');
  const snapshot = await getDocs(colRef);
  return snapshot.docs.map((doc) => ({
    id: doc.id,
    ...doc.data(),
  }));
};

// 6. Cloud Storage Attendance Photo Upload Helper
export const uploadAttendanceSelfieToStorage = async (fileOrBlob, employeeId, recordId) => {
  const storagePath = `attendance/${employeeId}/${recordId}/check-in.jpg`;
  const storageRef = ref(storage, storagePath);
  const snapshot = await uploadBytes(storageRef, fileOrBlob, {
    contentType: 'image/jpeg',
  });
  const downloadUrl = await getDownloadURL(snapshot.ref);
  return {
    storagePath,
    downloadUrl,
  };
};

// 7. Real-time Subscriptions for Cross-Platform Live Updates
export const subscribeToPendingEmployees = (callback, onError) => {
  if (!db) return () => {};
  try {
    const colRef = collection(db, 'employees');
    return onSnapshot(
      colRef,
      (snapshot) => {
        const employees = snapshot.docs.map((docSnap) => ({
          id: docSnap.id,
          _firestore_id: docSnap.id,
          ...docSnap.data(),
        }));
        callback(employees);
      },
      (error) => {
        if (onError) onError(error);
      }
    );
  } catch (err) {
    if (onError) onError(err);
    return () => {};
  }
};

export const subscribeToAttendanceRecords = (callback, onError) => {
  if (!db) return () => {};
  try {
    const colRef = collection(db, 'attendance');
    return onSnapshot(
      colRef,
      (snapshot) => {
        const records = snapshot.docs.map((docSnap) => ({
          id: docSnap.id,
          ...docSnap.data(),
        }));
        callback(records);
      },
      (error) => {
        if (onError) onError(error);
      }
    );
  } catch (err) {
    if (onError) onError(err);
    return () => {};
  }
};

