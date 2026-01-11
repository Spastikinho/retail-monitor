import Link from 'next/link';
import { FileQuestion, Home, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-6">
          <FileQuestion className="h-8 w-8 text-gray-400" />
        </div>

        <h1 className="text-4xl font-bold text-gray-900 mb-2">404</h1>
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Page not found</h2>
        <p className="text-gray-500 mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>

        <div className="flex justify-center gap-4">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Home className="h-4 w-4" />
            Go to Dashboard
          </Link>
        </div>

        <div className="mt-8 text-sm text-gray-400">
          <p>Looking for something?</p>
          <div className="mt-2 space-x-4">
            <Link href="/import" className="text-primary-600 hover:underline">Import URLs</Link>
            <Link href="/products" className="text-primary-600 hover:underline">Products</Link>
            <Link href="/settings" className="text-primary-600 hover:underline">Settings</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
