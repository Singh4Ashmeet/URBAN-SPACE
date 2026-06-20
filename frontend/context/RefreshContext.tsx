"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface RefreshContextType {
  refreshTrigger: number;
  refresh: () => void;
}

const RefreshContext = createContext<RefreshContextType>({
  refreshTrigger: 0,
  refresh: () => {},
});

export function RefreshProvider({ children }: { children: ReactNode }) {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <RefreshContext.Provider value={{ refreshTrigger, refresh }}>
      {children}
    </RefreshContext.Provider>
  );
}

export function useRefresh() {
  return useContext(RefreshContext);
}
