<x-app-layout>
    @push('title', __('Account created!'))

    <div class="col-span-12">
        <x-content.content-card icon="hotel-icon" classes="flex flex-col gap-y-8">
            <x-slot:title>
                {{ __('Welcome to :hotel, :username!', ['hotel' => setting('hotel_name'), 'username' => $username]) }}
            </x-slot:title>

            <x-slot:under-title>
                {{ __('Your account was created. This is your password — keep it somewhere safe, you will need it to log in again.') }}
            </x-slot:under-title>

            <div class="w-full !lg:w-[420px]">
                <div class="bg-[#efefef] rounded-md p-4 flex flex-col gap-y-3 dark:bg-gray-900">
                    <div class="flex items-center justify-between gap-x-4">
                        <div class="flex flex-col">
                            <span class="text-xs font-semibold text-gray-500 dark:text-gray-400">{{ __('Username') }}</span>
                            <span class="text-lg font-bold text-gray-900 dark:text-white">{{ $username }}</span>
                        </div>
                        <div class="flex flex-col">
                            <span class="text-xs font-semibold text-gray-500 dark:text-gray-400">{{ __('Password') }}</span>
                            <span class="text-lg font-bold text-gray-900 dark:text-white select-all">{{ $password }}</span>
                        </div>
                    </div>

                    <div class="flex items-center gap-x-3">
                        <button type="button" data-copy-credentials="{{ $username }}:{{ $password }}"
                                class="px-3 py-1.5 text-sm font-semibold text-white bg-gray-800 hover:bg-gray-700 rounded-md dark:bg-gray-700 dark:hover:bg-gray-600">
                            {{ __('Copy credentials') }}
                        </button>

                        <span id="copy-feedback" class="text-xs text-green-600 hidden">{{ __('Copied!') }}</span>
                    </div>
                </div>

                <div class="mt-4">
                    <a href="{{ route('nitro-client') }}">
                        <x-form.primary-button classes="w-full justify-center">
                            {{ __('Enter the hotel') }}
                        </x-form.primary-button>
                    </a>
                </div>
            </div>
        </x-content.content-card>
    </div>

    <script>
        document.querySelector('[data-copy-credentials]').addEventListener('click', (event) => {
            navigator.clipboard.writeText(event.currentTarget.dataset.copyCredentials);
            const feedback = document.getElementById('copy-feedback');
            feedback.classList.remove('hidden');
            setTimeout(() => feedback.classList.add('hidden'), 2000);
        });
    </script>
</x-app-layout>