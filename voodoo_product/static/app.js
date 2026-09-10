// Compatibility shim: legacy console entrypoint now delegates to the control-room client.
(function loadControlRoomClient() {
  const existing = document.querySelector('script[data-voodoo-control-room]');
  if (existing) {
    return;
  }
  const script = document.createElement('script');
  script.src = '/console/assets/control_room.js';
  script.defer = true;
  script.dataset.voodooControlRoom = 'true';
  document.head.appendChild(script);
}());
