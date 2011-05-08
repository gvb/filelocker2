using System;
using System.Resources;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using Microsoft.Win32;

namespace WinFilelocker
{
    public partial class SettingsForm : Form
    {
        public SettingsForm()
        {
            InitializeComponent();
        }

        private void Settings_Load(object sender, EventArgs e)
        {
            RegistryKey rkApp = Registry.CurrentUser.OpenSubKey("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run", true);
            if (rkApp.GetValue("Filelocker Client") == null)
            {
                chkRunOnStartup.Checked = false;
            }
            else
            {
                chkRunOnStartup.Checked = true;
            }

        }

        private void btnVerifyAndSave_Click(object sender, EventArgs e)
        {
            RegistryKey rkApp = Registry.CurrentUser.OpenSubKey("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run", true);
            if (chkRunOnStartup.Checked && rkApp.GetValue("Filelocker Client") == null)
            {
                rkApp.SetValue("Filelocker Client", Application.ExecutablePath.ToString());
            }
            else
            {
                if (rkApp.GetValue("Filelocker Client") != null)
                    rkApp.DeleteValue("Filelocker Client", false);
            }
            // Check to see the current state (running at startup or not)

            //if (rkApp.GetValue("MyApp") == null)
            //{
            //    // The value doesn't exist, the application is not set to run at startup
            //    chkRun.Checked = false;
            //}
            //else
            //{
            //    // The value exists, the application is set to run at startup
            //    chkRun.Checked = true;
            //}
        }


    }
}
