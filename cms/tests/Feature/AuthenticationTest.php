<?php

use App\Models\User;

test('users can authenticate using the login screen', function () {
    $user = User::factory()->create();

    $response = $this->post('/login', [
        'username' => $user->username,
        'password' => 'password',
    ]);

    expect($response->status())->toBe(302)
        ->and(auth()->check())->toBeTrue()
        ->and(parse_url($response->headers->get('Location'), PHP_URL_PATH))->toBe('/user/me');
});

test('users can not authenticate with invalid password', function () {
    $user = User::factory()->create();

    $this->post('/login', [
        'username' => $user->username,
        'password' => 'wrong-password',
    ]);

    expect(auth()->guest())->toBeTrue();
});
