using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using System.Drawing;

namespace WinFilelocker
{
    public class FilelockerTray : Form
    {
        NotifyIcon trayIcon = new NotifyIcon();
        ContextMenu trayMenu = new ContextMenu();
        public FilelockerTray()
        {
            initTray();
        }
        public FilelockerTray(string message)
        {
            initTray();
            trayIcon.BalloonTipTitle = "Successfully Registered to Filelocker Server";
            trayIcon.BalloonTipText = "The Filelocker client application succesfully registered to the Filelocker server and now running in the system tray";
            trayIcon.ShowBalloonTip(3000);
        }

        private void initTray()
        {
            //Application.Run(new FilelockerTrayApp()
            trayMenu.MenuItems.Add("Exit", OnExit);

            //Create a tray icon
            trayIcon = new NotifyIcon();
            trayIcon.Text = "Filelocker";
            trayIcon.Icon = new Icon(SystemIcons.Information, 40, 40);

            //Add menu to try icon and show it
            trayIcon.ContextMenu = trayMenu;
            trayIcon.Visible = true;
        }


        protected override void OnLoad(EventArgs e)
        {
            Visible = false;
            ShowInTaskbar = true;
            base.OnLoad(e);
        }

        private void OnExit(object sender, EventArgs e)
        {
            Application.Exit();
        }
        protected override void Dispose(bool isDisposing)
        {
            if (isDisposing)
            {
                trayIcon.Dispose();
            }
            base.Dispose();
        }
    }
}
