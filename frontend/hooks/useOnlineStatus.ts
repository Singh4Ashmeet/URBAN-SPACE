"use client";

import { useEffect, useState } from "react";

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [hasCheckedStatus, setHasCheckedStatus] = useState(false);

  useEffect(() => {
    const update = () => {
      setIsOnline(navigator.onLine);
      setHasCheckedStatus(true);
    };
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  return hasCheckedStatus ? isOnline : null;
}
