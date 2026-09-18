<x-app-layout>
    @push('title', __('Invite'))

    <div class="col-span-12">
        <x-content.content-card icon="hotel-icon" classes="flex flex-col gap-y-8">
            <x-slot:title>
                {{ __('You have been invited!') }}
            </x-slot:title>

            <x-slot:under-title>
                {{ __('You were invited to :hotel by :inviter. Choose your username and we will create your account — the system generates a password for you.', ['hotel' => setting('hotel_name'), 'inviter' => $inviter->username ?? __('an user')]) }}
            </x-slot:under-title>

            <div class="flex w-full justify-between">
                <div class="w-full !lg:w-[420px]">
                    <form method="POST" action="{{ route('invite.redeem', $invite->code) }}">
                        @csrf

                        <div>
                            <div class="flex flex-col gap-y-2">
                                <x-form.label for="username">
                                    {{ __('Username') }}

                                    <x-slot:info>
                                        {{ __('Your username is what you will have to use, when logging into :hotel. It is also what other users will know you as, so make sure you select a username that you like!', ['hotel' => setting('hotel_name')]) }}
                                    </x-slot:info>
                                </x-form.label>
                            </div>

                            <x-form.input error-bag="invite" name="username" type="text"
                                          value="{{ old('username') }}" placeholder="{{ __('Username') }}"
                                          :autofocus="true"/>
                        </div>

                        <div class="mt-4 bg-[#efefef] rounded-md p-3 flex flex-col gap-y-1 dark:bg-gray-900">
                            <div class="flex items-center gap-x-3">
                                <input id="terms" type="checkbox" name="terms"
                                       class="mt-1 rounded ring-0 focus:ring-0">

                                <a href="{{ route('help-center.rules.index') }}" target="_blank"
                                   class="mt-1 text-sm font-semibold text-gray-700 hover:text-gray-900 hover:underline dark:hover:text-gray-300 dark:text-gray-500">
                                    {{ __('I accept the :hotel terms & rules.', ['hotel' => setting('hotel_name')]) }}
                                </a>
                            </div>

                            @error('terms', 'invite')
                            <p class="mt-1 text-xs italic text-red-500">
                                {{ $message }}
                            </p>
                            @enderror
                        </div>

                        @if (setting('cloudflare_turnstile_enabled'))
                            <x-turnstile />
                        @endif

                        <div class="mt-4">
                            <x-form.primary-button>
                                {{ __('Create my account') }}
                            </x-form.primary-button>
                        </div>
                    </form>
                </div>

                <div class="hidden md:block relative w-full">
                    <img class="opacity-50 absolute -right-3 -bottom-3" src="{{ asset('/assets/images/hotel.png') }}"
                         alt="">
                </div>
            </div>
        </x-content.content-card>
    </div>
</x-app-layout>