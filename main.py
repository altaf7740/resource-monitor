import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import psutil
import csv
import os
import time
from datetime import datetime, timedelta
import platform
import psutil
import cpuinfo

class UsageMonitor:
    def __init__(self, email, password, recipient_emails):
        self.email = email
        self.password = password
        self.recipient_emails = recipient_emails
        self.today = datetime.now().strftime("%Y-%m-%d")

    def send_email(self, subject, body, attachments=None):
        """
        Sends an email with given parameters and attachments.
        """
        msg = MIMEMultipart()
        msg['From'] = self.email
        msg['To'] = ', '.join(self.recipient_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        if attachments:
            for attachment in attachments:
                with open(attachment, "rb") as f:
                    if attachment.endswith(".png"):
                        img = MIMEImage(f.read())
                        img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment))
                        msg.attach(img)
                    elif attachment.endswith(".csv"):
                        df = pd.read_csv(attachment, names=["Timestamp", "RAM", "CPU"])
                        df.to_csv(attachment, index=False)
                        csv_part = MIMEApplication(f.read(), Name=os.path.basename(attachment))
                        csv_part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(attachment)
                        msg.attach(csv_part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)

    def get_system_info(self):
        system_info = {}

        # Get OS information
        os_name = platform.system()
        os_release = platform.release()
        os_version = platform.version()
        os_fullname = platform.platform()
        system_info['os'] = f"{os_name} {os_version} ({os_fullname})"

        # Get total memory size
        mem_info = psutil.virtual_memory()
        system_info['memory_size'] = f"{mem_info.total / (1024 ** 3)}GB"

        # Get CPU model
        cpu_info = cpuinfo.get_cpu_info()
        system_info['cpu_model'] = cpu_info['brand_raw']

        # Get GPU information (if available)
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            gpu_info = []
            for gpu in gpus:
                gpu_info.append(gpu.name)
            system_info['graphics'] = gpu_info
        except ImportError:
            system_info['graphics'] = "GPUtil not installed"

        # Get storage information
        disk_info = psutil.disk_usage('/')
        system_info['storage'] = f"{disk_info.total / (1024 ** 3)}GB"

        return system_info

    def get_usage(self):
        """
        Returns CPU and RAM usage as percentages and timestamp.
        """
        cpu_percent = psutil.cpu_percent()
        ram_percent = psutil.virtual_memory().percent
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return timestamp, ram_percent, cpu_percent

    def write_to_csv(self, timestamp, ram_percent, cpu_percent):
        """
        Writes usage data to a CSV file.
        """
        with open(f'usage_{self.today}.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, ram_percent, cpu_percent])

    def send_email_report(self):
        """
        Sends daily CPU and RAM usage report via email.
        """
        info = self.get_system_info()
        subject = "Daily CPU and RAM Usage Report | i-Tips"
        body = f"Hi, \n\nPlease find the daily CPU and RAM usage of below system report attached. \n\nOS: {info['os']}\nMemory Size: {info['memory_size']}\nCPU Model: {info['cpu_model']}\nGraphics: {info['graphics']}\nStorage Size: {info['storage']}\n\nThank you.\ni-Tips Bot"
        plot_path = self.plot_usage()
        attachments = [plot_path, f'usage_{self.today}.csv']
        self.send_email(subject, body, attachments)
        for attachment in attachments:
            os.remove(attachment)
        self.today = datetime.now().strftime("%Y-%m-%d")

    def read_usage_data(self):
        """
        Reads usage data from CSV file.
        """
        df = pd.read_csv(f'usage_{self.today}.csv', names=["Timestamp", "RAM", "CPU"])
        return df.to_string(index=False)

    def plot_usage(self):
        """
        Plots CPU and RAM usage with 30-minute intervals and returns the plot file path.
        """
        df = pd.read_csv(f'usage_{self.today}.csv', names=["Timestamp", "RAM", "CPU"])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d %H:%M:%S')
        df.set_index('Timestamp', inplace=True)
        df_resampled = df.resample('1T').mean()

        plt.figure(figsize=(10*3, 6))
        plt.plot(df_resampled.index, df_resampled["RAM"], label="RAM (%)")
        plt.plot(df_resampled.index, df_resampled["CPU"], label="CPU (%)")
        plt.xlabel("Time")
        plt.ylabel("Usage")
        plt.title("CPU and RAM Usage (Per minute intervals)")
        plt.legend()

        # Adjust x-axis labels
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: time.strftime('%H:%M:%S', time.localtime(x))))
        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(10))  # Adjust the number of ticks on the x-axis as needed
        plt.tight_layout()
        plot_path = "graph.png"
        plt.savefig(plot_path)
        plt.close()  # Close the plot to free up resources
        return plot_path


if __name__ == "__main__":
    SENDER = os.getenv('RESOURCE_MONITOR_SENDER_MAIL')
    PASSWORD = os.getenv('RESOURCE_MONITOR_SENDER_PASSWORD')
    RECEIVER = [
    ]
    STOP_TIME = "23:59:59"
    if all([SENDER, PASSWORD, RECEIVER]):
        monitor = UsageMonitor(SENDER, PASSWORD, RECEIVER)
        while True:
            timestamp, ram_percent, cpu_percent = monitor.get_usage()
            monitor.write_to_csv(timestamp, ram_percent, cpu_percent)
            time.sleep(1) 

            # Check if it's the end of the day
            if datetime.now().strftime("%H:%M:%S") == STOP_TIME:
                monitor.send_email_report()

