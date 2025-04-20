
import { Toast, ToastActionElement, ToastProps } from "@/components/ui/toast";
import {
  useState,
  createContext,
  useContext,
  type FC,
  type ReactNode,
} from "react";

type ToasterToast = ToastProps & {
  id: string;
  title?: ReactNode;
  description?: ReactNode;
  action?: ToastActionElement;
};

const ToastContext = createContext<{
  toasts: ToasterToast[];
  addToast: (toast: Omit<ToasterToast, "id">) => void;
  dismissToast: (toastId: string) => void;
  updateToast: (toast: ToasterToast) => void;
}>({
  toasts: [],
  addToast: () => {},
  dismissToast: () => {},
  updateToast: () => {},
});

export const useToast = () => {
  const context = useContext(ToastContext);

  if (context === undefined) {
    throw new Error("useToast must be used within a ToastProvider");
  }

  return {
    toast: context.addToast,
    dismiss: context.dismissToast,
    update: context.updateToast,
    toasts: context.toasts,
  };
};

export const ToastProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToasterToast[]>([]);

  const addToast = (toast: Omit<ToasterToast, "id">) => {
    const id = Math.random().toString(36).substring(2, 9);

    setToasts((prevToasts) => [
      ...prevToasts,
      { id, ...toast },
    ]);

    return id;
  };

  const dismissToast = (toastId: string) => {
    setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== toastId));
  };

  const updateToast = (toast: ToasterToast) => {
    setToasts((prevToasts) =>
      prevToasts.map((t) => (t.id === toast.id ? { ...t, ...toast } : t))
    );
  };

  return (
    <ToastContext.Provider
      value={{
        toasts,
        addToast,
        dismissToast,
        updateToast,
      }}
    >
      {children}
    </ToastContext.Provider>
  );
};

// A simple function to add a toast directly
export const toast = (props: Omit<ToasterToast, "id">) => {
  const { toast: addToast } = useToast();
  return addToast(props);
};
