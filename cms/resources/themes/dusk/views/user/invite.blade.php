<x-app-layout>
    @push('title', __('Invite friends'))

    <div class="col-span-12">
        <x-content.content-card icon="hotel-icon" classes="flex flex-col gap-y-8">
            <x-slot:title>
                {{ __('Invite friends') }}
            </x-slot:title>

            <x-slot:under-title>
                {{ __('Generate a link and send it to a friend. When they click it, they choose a username and the system creates their account with a generated password — then they can jump straight into the hotel.') }}
            </x-slot:under-title>

            <div class="w-full !lg:w-[420px] flex flex-col gap-y-4">
                <form method="POST" action="{{ route('invite.store') }}" class="flex items-end gap-x-3">
                    @csrf

                    <div class="flex-1">
                        <div class="flex flex-col gap-y-2">
                            <x-form.label for="max_uses">
                                {{ __('Max uses') }}
                            </x-form.label>
                        </div>

                        <x-form.input error-bag="invite" name="max_uses" type="number" min="1" max="100"
                                      value="{{ old('max_uses', 1) }}"/>
                    </div>

                    <x-form.primary-button>
                        {{ __('Generate') }}
                    </x-form.primary-button>
                </form>

                @if (session('generated_invite'))
                    <div class="bg-green-50 dark:bg-gray-900 rounded-md p-4 flex flex-col gap-y-2">
                        <span class="text-sm font-semibold text-green-700 dark:text-green-400">{{ __('Your invite link is ready!') }}</span>

                        <div class="flex items-center gap-x-2">
                            <input type="text" readonly value="{{ route('invite.show', session('generated_invite')->code) }}"
                                   class="w-full text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md px-3 py-2 select-all">

                            <button type="button" data-copy="{{ route('invite.show', session('generated_invite')->code) }}"
                                    class="px-3 py-2 text-sm font-semibold text-white bg-green-600 hover:bg-green-500 rounded-md shrink-0">
                                {{ __('Copy') }}
                            </button>
                        </div>
                    </div>

                    <script>
                        document.querySelector('[data-copy]').addEventListener('click', (event) => {
                            navigator.clipboard.writeText(event.currentTarget.dataset.copy);
                        });
                    </script>
                @endif

                @if ($invites->isNotEmpty())
                    <div class="mt-2 flex flex-col gap-y-2">
                        @foreach ($invites as $invite)
                            <div class="flex items-center justify-between bg-[#efefef] dark:bg-gray-900 rounded-md px-4 py-3">
                                <div class="flex flex-col">
                                    <span class="text-sm font-semibold text-gray-900 dark:text-white">{{ $invite->code }}</span>
                                    <span class="text-xs text-gray-500 dark:text-gray-400">
                                        @if ($invite->used_by)
                                            {{ __('Used by :username', ['username' => $invite->user?->username ?? '?']) }}
                                        @else
                                            {{ __('Not used yet') }}
                                        @endif
                                    </span>
                                </div>

                                <div class="flex items-center gap-x-2">
                                    <span class="text-xs text-gray-400">{{ $invite->max_uses }}x</span>
                                    <a href="{{ route('invite.show', $invite->code) }}" target="_blank"
                                       class="text-xs font-semibold text-blue-600 hover:text-blue-500 hover:underline">
                                        {{ __('Open') }}
                                    </a>
                                </div>
                            </div>
                        @endforeach
                    </div>
                @endif
            </div>
        </x-content.content-card>
    </div>
</x-app-layout>