import { Dialog, Transition } from '@headlessui/react';
import { Fragment, ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: 'md' | 'lg' | 'xl';
}

export default function SideModal({ open, onClose, title, children, footer, width = 'md' }: Props) {
  const widthClass = { md: 'max-w-md', lg: 'max-w-2xl', xl: 'max-w-4xl' }[width];
  return (
    <Transition show={open} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-50">
        <Transition.Child as={Fragment}
          enter="ease-out duration-200" enterFrom="opacity-0" enterTo="opacity-100"
          leave="ease-in duration-150" leaveFrom="opacity-100" leaveTo="opacity-0">
          <div className="fixed inset-0 bg-black/40" aria-hidden="true" />
        </Transition.Child>
        <div className="fixed inset-0 flex justify-end">
          <Transition.Child as={Fragment}
            enter="ease-out duration-200" enterFrom="translate-x-full" enterTo="translate-x-0"
            leave="ease-in duration-150" leaveFrom="translate-x-0" leaveTo="translate-x-full">
            <Dialog.Panel className={`flex flex-col w-full ${widthClass} bg-bg-card shadow-2xl`}>
              <div className="flex-shrink-0 h-16 flex items-center justify-between px-6 border-b border-border-base">
                <Dialog.Title className="text-lg font-semibold text-text-primary">{title}</Dialog.Title>
                <button onClick={onClose} className="p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition-all">
                  <X className="h-5 w-5 text-text-secondary" />
                </button>
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto p-6">{children}</div>
              {footer && (
                <div className="flex-shrink-0 p-4 border-t border-border-base flex justify-end gap-2">{footer}</div>
              )}
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
